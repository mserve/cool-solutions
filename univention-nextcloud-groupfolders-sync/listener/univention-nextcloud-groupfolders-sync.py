# -*- coding: utf-8 -*-
#
# Copyright 2020 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.

__package__ = ""  # workaround for PEP 366
import subprocess
import listener

name = "univention-nextcloud-groupfolders-sync"
description = "creates and removes folders from nextcloud when adding/removing claases or working groups in schools"
filter = "(objectClass=ucsschoolGroup)"
attribute = ["cn"]


class AsRoot(object):
	"""
	Temporarily change effective UID to 'root'.
	"""

	def __enter__(self):
		listener.setuid(0)

	def __exit__(self, exc_type, exc_value, traceback):
		listener.unsetuid()

def handler(dn, new, old):
		""" the mandatory handler for ldap listeners """

		if new and not old:
				handler_add(dn, new)
		elif new and old:
				handler_modify(dn, old, new)
		elif not new and old:
				handler_remove(dn, old)
		else:
				pass  # ignore


def handler_add(dn, new):
		"""Handle addition of object."""

		(school, objname) = new['cn'][0].split('-', 1)
		cmd = ["/usr/sbin/univention-nextcloud-groupfolders-sync", "create", school, objname]

		with AsRoot():
			subprocess.check_call(cmd)


def handler_modify(dn, old, new):
		"""Handle modification of object."""
		pass  # replace this


def handler_remove(dn, old):
		"""Handle removal of object."""
		oldcn = new['cn'][0]

		with AsRoot():
			subprocess.check_call(
					["/usr/sbin/univention-nextcloud-groupfolders-sync", "delete", oldcn]
			)