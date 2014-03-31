import sys
sys.path.append('/Library/AutoPkg/autopkglib')
from autopkglib import Processor, ProcessorError

import os
import subprocess
from xml.etree import ElementTree
from distutils import version

__all__ = ["MunkiServerImporter"]

class MunkiServerImporter(Processor):
	input_variables = {
		"MUNKISERVER_ADDR": {
			"description": "Root URL of a MunkiServer installation",
			"required": True
		},
		"MUNKISERVER_USER": {
			"description": "User name on a MunkiServer installation",
			"required": True
		},
		"MUNKISERVER_PASSWORD": {
			"description": "Password for a MunkiServer installation",
			"required": True
		},
		"pkg_path": {
			"required": True,
			"description": "Path to a dmg to import.",
		},
		"munkiimport_pkgname": {
			"required": False,
			"description": "Corresponds to --pkgname option to munkiimport.",
		},
		"munkiimport_appname": {
			"required": False,
			"description": "Corresponds to --appname option to munkiimport.",
		},
		"munkiimport_name": {
			"required": False,
			"description": "Corresponds to the name key in the pkginfo.",
		},
		"version_comparison_key": {
			"required": False,
			"description": ("String to set 'version_comparison_key' for "
				"any generated installs items."),
		},
	}
	output_variables = {
		
	}
	
	cookiejar = '/tmp/autopkg.cookies'
	def curl(self, url, opt = [], data = {}):
		options = opt[:]
		for k in data:
			options.append('-F')
			options.append('%s=%s' % (k, data[k]))
		
		options += ['-s']
		options += ['-b', self.cookiejar]
		options += ['-c', self.cookiejar]
		options += [url]
		return subprocess.check_output(['/usr/bin/curl'] + options)
	
	def munkiserver_login(self):
		os.unlink(self.cookiejar)
		
		data = {}
		data['username'] = self.env['MUNKISERVER_USER']
		data['pass'] = self.env['MUNKISERVER_PASSWORD']

		# get the token from the login page
		url = self.env['MUNKISERVER_ADDR'] + '/login'
		resp = self.curl(url)
		xml = ElementTree.fromstring(resp)
		at = xml.find(".//{http://www.w3.org/1999/xhtml}input[@name='authenticity_token']")
		data['authenticity_token'] = at.attrib['value']
		
		# now log in
		url = self.env['MUNKISERVER_ADDR'] + '/create_session'
		resp = self.curl(url, data=data)
		if resp.find('Munki Server: index') <= 0 and resp.find('/dashboard">redirected') <= 0:
			raise Exception('Login to MunkiServer failed')
	
	def munkiserver_upload_package(self):
		data = {}
		data['package_file'] = '@' + self.env["pkg_path"]
		data['commit'] = 'Upload'
		if 'munkiimport_pkgname' in self.env:
			data['makepkginfo_options[pkgname]'] = self.env["munkiimport_pkgname"]
		if 'munkiimport_pkgname' in self.env:
			data['makepkginfo_options[appname]'] = self.env["munkiimport_appname"]
		if not 'munkiimport_pkgname' in self.env:
			self.env["munkiimport_name"] = ''
		data['makepkginfo_options[name]'] = self.env["munkiimport_name"]
		
		# request the upload form
		url = self.env['MUNKISERVER_ADDR'] + '/default/packages/add'
		resp = self.curl(url)
		if resp.find('Munki Server: new') <= 0:
			raise Exception('Do not have permission to upload new packages to MunkiServer')
		# extract the CSRF token
		xml = ElementTree.fromstring(resp)
		ct = xml.find(".//{http://www.w3.org/1999/xhtml}meta[@name='csrf-token']")
		options = ['-H', 'X-CSRF-Token: ' + ct.attrib['content']]
		
		# now perform the upload
		url = self.env['MUNKISERVER_ADDR'] + '/default/packages'
		resp = self.curl(url, options, data)
		xml = ElementTree.fromstring(resp)
		for msg in xml.findall(".//{http://www.w3.org/1999/xhtml}div[@class='message error']"):
			raise Exception(msg.text)
	
	def main(self):
		if not self.env["pkg_path"].endswith('.dmg'):
			raise Exception("Only DMGs are accepted by MunkiServer.")
		
		self.munkiserver_login()
		self.munkiserver_upload_package()
