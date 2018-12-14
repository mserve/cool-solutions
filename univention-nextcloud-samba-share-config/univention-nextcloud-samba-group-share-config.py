#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Nextcloud Samba share configuration
# listener module
#
# Copyright 2018 Univention GmbH
#
# http://www.univention.de/
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
# <http://www.gnu.org/licenses/>.

__package__='' 	# workaround for PEP 366

import listener
import re
import subprocess
import time
import univention.debug
import univention.admin.uldap
from univention.config_registry import ConfigRegistry
ucr = ConfigRegistry()
ucr.load()

name='nextcloud-samba-share-config'
description='Configure access to Samba shares in Nextcloud'
filter='(&(objectClass=nextcloudGroup)(nextcloudEnabled=1))'
attributes=[]

def initialize():
	univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "{}: initialize".format(name))
	return

def handler(dn, new, old):
	univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "DN {}".format(dn))
	listener.setuid(0)
	lo, po = univention.admin.uldap.getMachineConnection()

	windomain = ucr.get('windows/domain')

	groupCnRegex = '^cn=([^,]*)'
	domainUsersRegex = '^cn=Domain\ Users\ [A-Za-z0-9_]*'
	domainUsersOuRegex = '^cn=Domain\ Users\ '
	domainUsersMatch = re.match(domainUsersRegex, dn)

	groupCnMatch = re.match(groupCnRegex, dn)
	groupCn = re.sub('^cn=', '', groupCnMatch.group())

	if domainUsersMatch:
		shareName = "Marktplatz"
		ou = re.sub(domainUsersOuRegex, '', domainUsersMatch.group())
		mountName = "Marktplatz {}".format(ou)
		base = ucr.get('ldap/base')
		share = lo.get("cn=Marktplatz,cn=shares,ou={},{}".format(ou, base))
	else:
		shareDn = lo.search("(&(objectClass=univentionShareSamba)(cn={}))".format(groupCn))
		share = lo.get(shareDn[0][0])
		shareName = groupCn
		mountName = groupCn

	if share:
		# Enable files_external Nextcloud app; moved to postinst, too much overhead to do this on every single change
		#univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Making sure files_external app is enabled")
		#enableAppCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ app:enable files_external"
		#subprocess.call(enableAppCmd, shell=True)

		shareHost = ''.join(share['univentionShareHost'])
		shareSambaName = ''.join(share['univentionShareSambaName'])
		getMountIdCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:list | grep '\/{}' | awk '{{print $2}}'".format(mountName)

		mountId = subprocess.check_output(getMountIdCmd, shell=True)
		mountId = re.search('[0-9]*', mountId).group()
		if mountId:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Mount for {} is already configured. Re-setting config...".format(groupCn))
		else:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "No mount for {} configured yet. Configuring...".format(groupCn))
			createMountCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:create '/{}' smb 'password::sessioncredentials'".format(mountName)
			subprocess.call(createMountCmd, shell=True)
			mountId = subprocess.check_output(getMountIdCmd, shell=True)
			mountId = re.search('[0-9]*', mountId).group()

		addHostCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:config {} host {}".format(mountId, shareHost)
		addShareRootCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:config {} share '/'".format(mountId)
		addShareNameCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:config {} root '{}'".format(mountId, shareName)
		addShareDomainCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:config {} domain '{}'".format(mountId, windomain)
		#checkApplicableGroupCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ group:list | grep -E '\-\ {}:'".format(groupCn)
		checkApplicableGroupCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ group:adduser '{}' nc_admin".format(groupCn)
		cleanupApplicableGroupCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ group:removeuser '{}' nc_admin".format(groupCn)
		addApplicableGroupCmd = "univention-app shell nextcloud sudo -u www-data /var/www/html/occ files_external:applicable --add-group '{}' {}".format(groupCn, mountId)

		subprocess.call(addHostCmd, shell=True)
		subprocess.call(addShareRootCmd, shell=True)
		subprocess.call(addShareNameCmd, shell=True)
		subprocess.call(addShareDomainCmd, shell=True)
		ret = subprocess.call(checkApplicableGroupCmd, shell=True)
		timeout = time.time() + 15
		while ret != 0:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Group {} does not yet exist in Nextcloud, waiting till it exists with 15s timeout".format(groupCn))
			time.sleep(2)
			ret = subprocess.call(checkApplicableGroupCmd, shell=True)
			if time.time() > timeout:
				break
		if ret == 0:
			subprocess.call(addApplicableGroupCmd, shell=True)
			subprocess.call(cleanupApplicableGroupCmd, shell=True)
			listener.unsetuid()
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Finished share mount configuration for share {}".format(groupCn))
		else:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Group {} for share {} was not found in Nextcloud. Check ldapBaseGroups in Nextcloud ldap config.".format(groupCn, shareName))
	else:
		univention.debug.debug(univention.debug.LISTENER, univention.debug.WARN, "Nothing to do: no share was found for group {}".format(groupCn))

def clean():
	return

def postrun():
	return