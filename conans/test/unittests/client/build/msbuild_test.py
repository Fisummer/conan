import os
import platform
import unittest

import mock
from nose.plugins.attrib import attr
from parameterized import parameterized

from conans.client import tools
from conans.client.build.msbuild import MSBuild
from conans.errors import ConanException
from conans.model.version import Version
from conans.paths import CONANFILE
from conans.test.utils.conanfile import MockConanfile, MockSettings
from conans.test.utils.visual_project_files import get_vs_project_files


class MSBuildTest(unittest.TestCase):

    def dont_mess_with_build_type_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64",
                                 "compiler.runtime": "MDd"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        self.assertEquals(msbuild.build_env.flags, [])
        template = msbuild._get_props_file_contents()

        self.assertNotIn("-Ob0", template)
        self.assertNotIn("-Od", template)

        msbuild.build_env.flags = ["-Zi"]
        template = msbuild._get_props_file_contents()

        self.assertNotIn("-Ob0", template)
        self.assertNotIn("-Od", template)
        self.assertIn("-Zi", template)
        self.assertIn("<RuntimeLibrary>MultiThreadedDebugDLL</RuntimeLibrary>", template)

    def without_runtime_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        template = msbuild._get_props_file_contents()
        self.assertNotIn("<RuntimeLibrary>", template)

    def custom_properties_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("project_file.sln", properties={"MyProp1": "MyValue1",
                                                                      "MyProp2": "MyValue2"})
        self.assertIn('/p:MyProp1="MyValue1"', command)
        self.assertIn('/p:MyProp2="MyValue2"', command)

    @unittest.skipUnless(platform.system() == "Windows", "Requires MSBuild")
    def binary_logging_on_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "compiler.version": "15",
                                 "arch": "x86_64",
                                 "compiler.runtime": "MDd"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("dummy.sln", output_binary_log=True)
        self.assertIn("/bl", command)

    @unittest.skipUnless(platform.system() == "Windows", "Requires MSBuild")
    def binary_logging_on_with_filename_test(self):
        bl_filename = "a_special_log.log"
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "compiler.version": "15",
                                 "arch": "x86_64",
                                 "compiler.runtime": "MDd"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("dummy.sln", output_binary_log=bl_filename)
        expected_command = '/bl:"%s"' % bl_filename
        self.assertIn(expected_command, command)

    def binary_logging_off_explicit_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "compiler.version": "15",
                                 "arch": "x86_64",
                                 "compiler.runtime": "MDd"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("dummy.sln", output_binary_log=False)
        self.assertNotIn("/bl", command)

    def binary_logging_off_implicit_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "compiler.version": "15",
                                 "arch": "x86_64",
                                 "compiler.runtime": "MDd"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("dummy.sln")
        self.assertNotIn("/bl", command)

    @unittest.skipUnless(platform.system() == "Windows", "Requires MSBuild")
    @mock.patch("conans.client.build.msbuild.MSBuild.get_version")
    def binary_logging_not_supported_test(self, mock_get_version):
        mock_get_version.return_value = Version("14")

        mocked_settings = MockSettings({"build_type": "Debug",
                                        "compiler": "Visual Studio",
                                        "compiler.version": "15",
                                        "arch": "x86_64",
                                        "compiler.runtime": "MDd"})
        conanfile = MockConanfile(mocked_settings)
        except_text = "MSBuild version detected (14) does not support 'output_binary_log' ('/bl')"
        msbuild = MSBuild(conanfile)

        with self.assertRaises(ConanException) as exc:
            msbuild.get_command("dummy.sln", output_binary_log=True)
        self.assertIn(except_text, str(exc.exception))

    @unittest.skipUnless(platform.system() == "Windows", "Requires MSBuild")
    def get_version_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "compiler.version": "15",
                                 "arch": "x86_64",
                                 "compiler.runtime": "MDd"})
        version = MSBuild.get_version(settings)
        self.assertRegexpMatches(version, "(\d+\.){2,3}\d+")
        self.assertGreater(version, "15.1")

    def custom_properties_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("projecshould_flags_testt_file.sln", properties={"MyProp1": "MyValue1",
                                                                      "MyProp2": "MyValue2"})
        self.assertIn('/p:MyProp1="MyValue1"', command)
        self.assertIn('/p:MyProp2="MyValue2"', command)

    def verbosity_default_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("projecshould_flags_testt_file.sln")
        self.assertIn('/verbosity:minimal', command)

    def verbosity_env_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64"})
        with tools.environment_append({"CONAN_MSBUILD_VERBOSITY": "detailed"}):
            conanfile = MockConanfile(settings)
            msbuild = MSBuild(conanfile)
            command = msbuild.get_command("projecshould_flags_testt_file.sln")
            self.assertIn('/verbosity:detailed', command)

    def verbosity_explicit_test(self):
        settings = MockSettings({"build_type": "Debug",
                                 "compiler": "Visual Studio",
                                 "arch": "x86_64"})
        conanfile = MockConanfile(settings)
        msbuild = MSBuild(conanfile)
        command = msbuild.get_command("projecshould_flags_testt_file.sln", verbosity="quiet")
        self.assertIn('/verbosity:quiet', command)
