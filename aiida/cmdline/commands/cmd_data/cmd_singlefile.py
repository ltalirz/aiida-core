# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""`verdi data singlefile` command."""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from aiida.cmdline.commands.cmd_data import verdi_data
from aiida.cmdline.params import arguments, types
from aiida.cmdline.utils import decorators, echo


@verdi_data.group('singlefile')
def singlefile():
    """Work with SinglefileData nodes."""


@singlefile.command('content')
@arguments.DATA(type=types.DataParamType(sub_classes=('aiida.data:singlefile',)))
@decorators.with_dbenv()
def singlefile_content(data):
    """Show the content of the file."""
    for node in data:
        try:
            echo.echo(node.get_content())
        except IOError as exception:
            echo.echo_warning('could not read the content for SinglefileData<{}>: {}'.format(node.pk, str(exception)))
