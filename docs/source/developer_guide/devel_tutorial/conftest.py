# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-core #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
"""
For pytest
This file should be put into the root directory of the package to make
the fixtures available to all tests.
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
import tempfile
import shutil
import pytest

from aiida.manage.tests.pytest_fixtures import aiida_profile, clear_database, tempdir  # pylint: disable=unused-import