# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from aiida import orm
from aiida.backends.testbase import AiidaTestCase
from aiida.common import exceptions
from aiida.engine import launch, Process, WorkChain, calcfunction


@calcfunction
def add(a, b):
    return a + b


class AddWorkChain(WorkChain):

    @classmethod
    def define(cls, spec):
        super(AddWorkChain, cls).define(spec)
        spec.input('a', valid_type=orm.Int)
        spec.input('b', valid_type=orm.Int)
        spec.outline(cls.add)
        spec.output('result', valid_type=orm.Int)

    def add(self):
        self.out('result', orm.Int(self.inputs.a + self.inputs.b).store())


class TestLaunchers(AiidaTestCase):

    def setUp(self):
        super(TestLaunchers, self).setUp()
        self.assertIsNone(Process.current())
        self.a = orm.Int(1)
        self.b = orm.Int(2)
        self.result = 3

    def tearDown(self):
        super(TestLaunchers, self).tearDown()
        self.assertIsNone(Process.current())

    def test_calcfunction_run(self):
        result = launch.run(add, a=self.a, b=self.b)
        self.assertEquals(result, self.result)

    def test_calcfunction_run_get_node(self):
        result, node = launch.run_get_node(add, a=self.a, b=self.b)
        self.assertEquals(result, self.result)
        self.assertTrue(isinstance(node, orm.CalcFunctionNode))

    def test_calcfunction_run_get_pk(self):
        result, pk = launch.run_get_pk(add, a=self.a, b=self.b)
        self.assertEquals(result, self.result)
        self.assertTrue(isinstance(pk, int))

    def test_workchain_run(self):
        result = launch.run(AddWorkChain, a=self.a, b=self.b)
        self.assertEquals(result['result'], self.result)

    def test_workchain_run_get_node(self):
        result, node = launch.run_get_node(AddWorkChain, a=self.a, b=self.b)
        self.assertEquals(result['result'], self.result)
        self.assertTrue(isinstance(node, orm.WorkChainNode))

    def test_workchain_run_get_pk(self):
        result, pk = launch.run_get_pk(AddWorkChain, a=self.a, b=self.b)
        self.assertEquals(result['result'], self.result)
        self.assertTrue(isinstance(pk, int))

    def test_workchain_builder_run(self):
        builder = AddWorkChain.get_builder()
        builder.a = self.a
        builder.b = self.b
        result = launch.run(builder)
        self.assertEquals(result['result'], self.result)

    def test_workchain_builder_run_get_node(self):
        builder = AddWorkChain.get_builder()
        builder.a = self.a
        builder.b = self.b
        result, node = launch.run_get_node(builder)
        self.assertEquals(result['result'], self.result)
        self.assertTrue(isinstance(node, orm.WorkChainNode))

    def test_workchain_builder_run_get_pk(self):
        builder = AddWorkChain.get_builder()
        builder.a = self.a
        builder.b = self.b
        result, pk = launch.run_get_pk(builder)
        self.assertEquals(result['result'], self.result)
        self.assertTrue(isinstance(pk, int))

    def test_submit_store_provenance_false(self):
        """Verify that submitting with `store_provenance=False` raises."""
        with self.assertRaises(exceptions.InvalidOperation):
            launch.submit(AddWorkChain, a=self.a, b=self.b, metadata={'store_provenance': False})


class TestLaunchersDryRun(AiidaTestCase):
    """Test the launchers when performing a dry-run."""

    def setUp(self):
        super(TestLaunchersDryRun, self).setUp()
        self.assertIsNone(Process.current())

    def tearDown(self):
        import os
        import shutil
        from aiida.common.folders import CALC_JOB_DRY_RUN_BASE_PATH

        super(TestLaunchersDryRun, self).tearDown()
        self.assertIsNone(Process.current())

        # Make sure to clean the test directory that will be generated by the dry-run
        filepath = os.path.join(os.getcwd(), CALC_JOB_DRY_RUN_BASE_PATH)
        try:
            shutil.rmtree(filepath)
        except Exception:  # pylint: disable=broad-except
            pass

    def test_launchers_dry_run(self):
        """All launchers should work with `dry_run=True`, even `submit` which forwards to `run`."""
        from aiida.plugins import CalculationFactory

        ArithmeticAddCalculation = CalculationFactory('arithmetic.add')

        code = orm.Code(
            input_plugin_name='arithmetic.add',
            remote_computer_exec=[self.computer, '/bin/true']).store()

        inputs = {
            'code': code,
            'x': orm.Int(1),
            'y': orm.Int(1),
            'metadata': {
                'dry_run': True,
                'options': {
                    'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 1}
                }
            }
        }

        result = launch.run(ArithmeticAddCalculation, **inputs)
        self.assertEqual(result, {})

        result, pk = launch.run_get_pk(ArithmeticAddCalculation, **inputs)
        self.assertEqual(result, {})
        self.assertIsInstance(pk, int)

        result, node = launch.run_get_node(ArithmeticAddCalculation, **inputs)
        self.assertEqual(result, {})
        self.assertIsInstance(node, orm.CalcJobNode)
        self.assertIsInstance(node.dry_run_info, dict)
        self.assertIn('folder', node.dry_run_info)
        self.assertIn('script_filename', node.dry_run_info)

        node = launch.submit(ArithmeticAddCalculation, **inputs)
        self.assertIsInstance(node, orm.CalcJobNode)

    def test_launchers_dry_run_no_provenance(self):
        """Test the launchers in `dry_run` mode with `store_provenance=False`."""
        from aiida.plugins import CalculationFactory

        ArithmeticAddCalculation = CalculationFactory('arithmetic.add')

        code = orm.Code(
            input_plugin_name='arithmetic.add',
            remote_computer_exec=[self.computer, '/bin/true']).store()

        inputs = {
            'code': code,
            'x': orm.Int(1),
            'y': orm.Int(1),
            'metadata': {
                'dry_run': True,
                'store_provenance': False,
                'options': {
                    'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 1}
                }
            }
        }

        result = launch.run(ArithmeticAddCalculation, **inputs)
        self.assertEqual(result, {})

        result, pk = launch.run_get_pk(ArithmeticAddCalculation, **inputs)
        self.assertEqual(result, {})
        self.assertIsNone(pk)

        result, node = launch.run_get_node(ArithmeticAddCalculation, **inputs)
        self.assertEqual(result, {})
        self.assertIsInstance(node, orm.CalcJobNode)
        self.assertFalse(node.is_stored)
        self.assertIsInstance(node.dry_run_info, dict)
        self.assertIn('folder', node.dry_run_info)
        self.assertIn('script_filename', node.dry_run_info)

        node = launch.submit(ArithmeticAddCalculation, **inputs)
        self.assertIsInstance(node, orm.CalcJobNode)
        self.assertFalse(node.is_stored)
