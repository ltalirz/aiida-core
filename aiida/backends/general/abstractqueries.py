# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida_core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from abc import ABCMeta, abstractmethod
from six.moves import zip
import six


@six.add_metaclass(ABCMeta)
class AbstractQueryManager(object):
    def __init__(self, backend):
        """
        :param backend: The AiiDA backend
        :type backend: :class:`aiida.orm.implementation.backends.Backend`
        """
        self._backend = backend

    @abstractmethod
    def raw(self, query):
        """Execute a raw SQL statement and return the result.

        :param query: a string containing a raw SQL statement
        :return: the result of the query
        """
        pass

    def get_duplicate_node_uuids(self):
        """
        Return a list of nodes that have an identical UUID

        :return: list of tuples of (pk, uuid) of nodes with duplicate UUIDs
        """
        query = """
            SELECT s.id, s.uuid FROM (SELECT *, COUNT(*) OVER(PARTITION BY uuid) AS c FROM db_dbnode)
            AS s WHERE c > 1
            """
        return self.raw(query)

    def get_creation_statistics(
            self,
            user_pk=None
    ):
        """
        Return a dictionary with the statistics of node creation, summarized by day.

        :note: Days when no nodes were created are not present in the returned `ctime_by_day` dictionary.

        :param user_pk: If None (default), return statistics for all users.
            If user pk is specified, return only the statistics for the given user.

        :return: a dictionary as
            follows::

                {
                   "total": TOTAL_NUM_OF_NODES,
                   "types": {TYPESTRING1: count, TYPESTRING2: count, ...},
                   "ctime_by_day": {'YYYY-MMM-DD': count, ...}

            where in `ctime_by_day` the key is a string in the format 'YYYY-MM-DD' and the value is
            an integer with the number of nodes created that day.
        """
        from aiida.orm.querybuilder import QueryBuilder as QB
        from aiida.orm import User, Node
        from collections import Counter
        import datetime

        def count_statistics(dataset):

            def get_statistics_dict(dataset):
                results = {}
                for count, typestring in sorted(
                        (v, k) for k, v in dataset.items())[::-1]:
                    results[typestring] = count
                return results

            count_dict = {}

            types = Counter([r[2] for r in dataset])
            count_dict["types"] = get_statistics_dict(types)

            ctimelist = [r[1].strftime("%Y-%m-%d") for r in dataset]
            ctime = Counter(ctimelist)

            if len(ctimelist) > 0:

                # For the way the string is formatted, we can just sort it alphabetically
                firstdate = datetime.datetime.strptime(sorted(ctimelist)[0], '%Y-%m-%d')
                lastdate = datetime.datetime.strptime(sorted(ctimelist)[-1], '%Y-%m-%d')

                curdate = firstdate
                outdata = {}

                while curdate <= lastdate:
                    curdatestring = curdate.strftime('%Y-%m-%d')
                    outdata[curdatestring] = ctime.get(curdatestring, 0)
                    curdate += datetime.timedelta(days=1)
                count_dict["ctime_by_day"] = outdata

            else:
                count_dict["ctime_by_day"] = {}

            return count_dict

        statistics = {}

        q = QB()
        q.append(Node, project=['id', 'ctime', 'type'], tag='node')

        if user_pk is not None:
            q.append(User, creator_of='node', project='email', filters={'pk': user_pk})
        qb_res = q.all()

        # total count
        statistics["total"] = len(qb_res)
        statistics.update(count_statistics(qb_res))

        return statistics

    def get_bands_and_parents_structure(self, args):
        """
        Search for bands and return bands and the closest structure that is a parent of the instance.
        This is the backend independent way, can be overriden for performance reason

        :returns:
            A list of sublists, each latter containing (in order):
                pk as string, formula as string, creation date, bandsdata-label
        """

        import datetime
        from aiida.utils import timezone
        from aiida.orm.querybuilder import QueryBuilder
        from aiida.orm.data.structure import (get_formula, get_symbols_string)
        from aiida.orm.data.array.bands import BandsData
        from aiida.orm.data.structure import StructureData
        from aiida import orm

        qb = QueryBuilder()
        if args.all_users is False:
            user = orm.User.objects.get_default()
            qb.append(orm.User, tag="creator", filters={"email": user.email})
        else:
            qb.append(orm.User, tag="creator")

        bdata_filters = {}
        if args.past_days is not None:
            now = timezone.now()
            n_days_ago = now - datetime.timedelta(days=args.past_days)
            bdata_filters.update({"ctime": {'>=': n_days_ago}})

        qb.append(BandsData, tag="bdata", created_by="creator",
                  filters=bdata_filters,
                  project=["id", "label", "ctime"]
                  )

        group_filters = {}

        if args.group_name is not None:
            group_filters.update({"name": {"in": args.group_name}})
        if args.group_pk is not None:
            group_filters.update({"id": {"in": args.group_pk}})
        if group_filters:
            qb.append(orm.Group, tag="group", filters=group_filters,
                      group_of="bdata")

        qb.append(StructureData, tag="sdata", ancestor_of="bdata",
                  # We don't care about the creator of StructureData
                  project=["id", "attributes.kinds", "attributes.sites"])

        qb.order_by({StructureData: {'ctime': 'desc'}})

        list_data = qb.distinct()

        entry_list = []
        already_visited_bdata = set()

        for [bid, blabel, bdate, sid, akinds, asites] in list_data.all():

            # We process only one StructureData per BandsData.
            # We want to process the closest StructureData to
            # every BandsData.
            # We hope that the StructureData with the latest
            # creation time is the closest one.
            # This will be updated when the QueryBuilder supports
            # order_by by the distance of two nodes.
            if already_visited_bdata.__contains__(bid):
                continue
            already_visited_bdata.add(bid)

            if args.element is not None:
                all_symbols = [_["symbols"][0] for _ in akinds]
                if not any([s in args.element for s in all_symbols]
                           ):
                    continue

            if args.element_only is not None:
                all_symbols = [_["symbols"][0] for _ in akinds]
                if not all(
                        [s in all_symbols for s in args.element_only]
                ):
                    continue

            # We want only the StructureData that have attributes
            if akinds is None or asites is None:
                continue

            symbol_dict = {}
            for k in akinds:
                symbols = k['symbols']
                weights = k['weights']
                symbol_dict[k['name']] = get_symbols_string(symbols,
                                                            weights)

            try:
                symbol_list = []
                for s in asites:
                    symbol_list.append(symbol_dict[s['kind_name']])
                formula = get_formula(symbol_list,
                                      mode=args.formulamode)
            # If for some reason there is no kind with the name
            # referenced by the site
            except KeyError:
                formula = "<<UNKNOWN>>"
            entry_list.append([str(bid), str(formula),
                               bdate.strftime('%d %b %Y'), blabel])

        return entry_list

    def get_all_parents(self, node_pks, return_values=('id',)):
        """
        Get all the parents of given nodes
        :param node_pks: one node pk or an iterable of node pks
        :return: a list of aiida objects with all the parents of the nodes
        """
        from aiida.orm.querybuilder import QueryBuilder
        from aiida.orm import Node
        qb = QueryBuilder()
        qb.append(Node, tag='low_node',
                  filters={'id': {'in': node_pks}})
        qb.append(Node, ancestor_of='low_node', project=return_values)
        return qb.all()
