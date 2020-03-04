#!/usr/bin/env python

import os
import subprocess
import plistlib

from autopkglib import Processor, ProcessorError

__all__ = ["NvidiaDriverURLProvider"]

CHECK_URL = 'https://gfestage.nvidia.com/mac-update'
PLIST_FN  = 'nvidia_driver_macos.plist'

class NvidiaDriverURLProvider(Processor):
	'''Provides URL to the latest Web Driver download from NVIDIA.'''

	input_variables = {}

	output_variables = {
		'url1': {
			'description': 'URL to the Web Driver DMG download for the latest macOS build (usually a machine-specific build).'
		},
		'url2': {
			'description': 'URL to the Web Driver DMG download for the second-latest macOS build.'
		},
		'url3': {
			'description': 'URL to the Web Driver DMG download for the latest build of the previous macOS major version.'
		},
	}

	description = __doc__


	def get_url(self):
		try:
			plist_text = subprocess.check_output(['/usr/bin/curl', '-s', '-1', CHECK_URL])
		except BaseException as e:
			print(e)
			raise ProcessorError('Could not retrieve check URL %s' % CHECK_URL)

		plist_filename = os.path.join(self.env['RECIPE_CACHE_DIR'], PLIST_FN)

		try:
			plistf = open(plist_filename, 'w')
			plistf.write(plist_text)
			plistf.close()
		except:
			raise ProcessorError('Could not write NVIDIA plist file %s' % plist_filename)

		try:
			plist = plistlib.readPlist(plist_filename)
		except:
			raise ProcessorError('Could not read NVIDIA plist file %s' % plist_filename)

                result = []

                result.append( plist['updates'][0]['downloadURL'] )
                result.append( plist['updates'][0]['version'] )
                result.append( plist['updates'][0]['OS'] )
                result.append( plist['updates'][1]['downloadURL'] )
                result.append( plist['updates'][1]['version'] )
                result.append( plist['updates'][1]['OS'] )

                current_major = int(plist['updates'][0]['OS'][:2])
                for update in plist['updates'][2:]:
                    major = int(update['OS'][:2])
                    if major < current_major:
                        result.append( update['downloadURL'] )
                        result.append( update['version'] )
                        result.append( update['OS'] )
                        break

		return result

        def build_to_ver(self, build):
                major = 10
                minor = int(build[:2])-4
                patch = ord(build[2])-65
                return "%d.%d.%d" % (major,minor,patch)

	def main(self):
                result = self.get_url()

		self.env['url1'], self.env['url2'], self.env['url3'] = result[0::3]
		self.env['version1'], self.env['version2'], self.env['version3'] = result[1::3]
		self.env['build1'], self.env['build2'], self.env['build3'] = result[2::3]
                self.env['os1'], self.env['os2'], self.env['os3'] = self.build_to_ver(self.env['build1']), self.build_to_ver(self.env['build2']), self.build_to_ver(self.env['build3'])
		self.output('File URL %s, Version number %s, macOS %s build %s' % (self.env['url1'], self.env['os1'], self.env['version1'], self.env['build1']))
		self.output('File URL %s, Version number %s, macOS %s build %s' % (self.env['url2'], self.env['os2'], self.env['version2'], self.env['build2']))
		self.output('File URL %s, Version number %s, macOS %s build %s' % (self.env['url3'], self.env['os3'], self.env['version3'], self.env['build3']))

if __name__ == '__main__':
	processor = NvidiaDriverURLProvider()
	processor.execute_shell()
