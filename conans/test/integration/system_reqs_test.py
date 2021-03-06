import os
import unittest

from conans.model.ref import ConanFileReference, PackageReference
from conans.test.utils.tools import NO_SETTINGS_PACKAGE_ID, TestClient
from conans.util.files import load

base_conanfile = '''
from conans import ConanFile

class TestSystemReqs(ConanFile):
    name = "Test"
    version = "0.1"
    options = {"myopt": [True, False]}
    default_options = "myopt=True"

    def system_requirements(self):
        self.output.info("*+Running system requirements+*")
        %GLOBAL%
        return "Installed my stuff"
'''


class SystemReqsTest(unittest.TestCase):

    def force_system_reqs_rerun_test(self):
        client = TestClient()
        files = {'conanfile.py': base_conanfile.replace("%GLOBAL%", "")}
        client.save(files)
        client.run("create . user/channel")
        self.assertIn("*+Running system requirements+*", client.user_io.out)
        client.run("install Test/0.1@user/channel")
        self.assertNotIn("*+Running system requirements+*", client.user_io.out)
        ref = ConanFileReference.loads("Test/0.1@user/channel")
        pfs = client.cache.packages(ref)
        pid = os.listdir(pfs)[0]
        reqs_file = client.cache.system_reqs_package(PackageReference(ref, pid))
        os.unlink(reqs_file)
        client.run("install Test/0.1@user/channel")
        self.assertIn("*+Running system requirements+*", client.user_io.out)
        self.assertTrue(os.path.exists(reqs_file))

    def local_system_requirements_test(self):
        client = TestClient()
        files = {'conanfile.py': base_conanfile.replace("%GLOBAL%", "")}
        client.save(files)
        client.run("install .")
        self.assertIn("*+Running system requirements+*", client.user_io.out)

        files = {'conanfile.py': base_conanfile.replace("%GLOBAL%", "self.run('fake command!')")}
        client.save(files)
        with self.assertRaisesRegexp(Exception, "Command failed"):
            client.run("install .")

    def per_package_test(self):
        client = TestClient()
        files = {'conanfile.py': base_conanfile.replace("%GLOBAL%", "")}
        client.save(files)
        client.run("export . user/testing")
        client.run("install Test/0.1@user/testing --build missing")
        self.assertIn("*+Running system requirements+*", client.user_io.out)
        ref = ConanFileReference.loads("Test/0.1@user/testing")
        self.assertFalse(os.path.exists(client.cache.system_reqs(ref)))
        pref = PackageReference(ref, "f0ba3ca2c218df4a877080ba99b65834b9413798")
        load_file = load(client.cache.system_reqs_package(pref))
        self.assertIn("Installed my stuff", load_file)

        # Run again
        client.run("install Test/0.1@user/testing --build missing")
        self.assertNotIn("*+Running system requirements+*", client.user_io.out)
        self.assertFalse(os.path.exists(client.cache.system_reqs(ref)))
        load_file = load(client.cache.system_reqs_package(pref))
        self.assertIn("Installed my stuff", load_file)

        # Run with different option
        client.run("install Test/0.1@user/testing -o myopt=False --build missing")
        self.assertIn("*+Running system requirements+*", client.user_io.out)
        self.assertFalse(os.path.exists(client.cache.system_reqs(ref)))
        pref2 = PackageReference(ref, NO_SETTINGS_PACKAGE_ID)
        load_file = load(client.cache.system_reqs_package(pref2))
        self.assertIn("Installed my stuff", load_file)

        # remove packages
        client.run("remove Test* -f -p 544")
        self.assertTrue(os.path.exists(client.cache.system_reqs_package(pref)))
        client.run("remove Test* -f -p f0ba3ca2c218df4a877080ba99b65834b9413798")
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref)))
        self.assertTrue(os.path.exists(client.cache.system_reqs_package(pref2)))
        client.run("remove Test* -f -p %s" % NO_SETTINGS_PACKAGE_ID)
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref)))
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref2)))

    def global_test(self):
        client = TestClient()
        files = {'conanfile.py': base_conanfile.replace("%GLOBAL%",
                                                        "self.global_system_requirements=True")}
        client.save(files)
        client.run("export . user/testing")
        client.run("install Test/0.1@user/testing --build missing")
        self.assertIn("*+Running system requirements+*", client.user_io.out)
        ref = ConanFileReference.loads("Test/0.1@user/testing")
        pref = PackageReference(ref, "a527106fd9f2e3738a55b02087c20c0a63afce9d")
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref)))
        load_file = load(client.cache.system_reqs(ref))
        self.assertIn("Installed my stuff", load_file)

        # Run again
        client.run("install Test/0.1@user/testing --build missing")
        self.assertNotIn("*+Running system requirements+*", client.user_io.out)
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref)))
        load_file = load(client.cache.system_reqs(ref))
        self.assertIn("Installed my stuff", load_file)

        # Run with different option
        client.run("install Test/0.1@user/testing -o myopt=False --build missing")
        self.assertNotIn("*+Running system requirements+*", client.user_io.out)
        pref2 = PackageReference(ref, "54c9626b48cefa3b819e64316b49d3b1e1a78c26")
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref)))
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref2)))
        load_file = load(client.cache.system_reqs(ref))
        self.assertIn("Installed my stuff", load_file)

        # remove packages
        client.run("remove Test* -f -p")
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref)))
        self.assertFalse(os.path.exists(client.cache.system_reqs_package(pref2)))
        self.assertFalse(os.path.exists(client.cache.system_reqs(ref)))

    def wrong_output_test(self):
        client = TestClient()
        files = {'conanfile.py':
                 base_conanfile.replace("%GLOBAL%", "").replace('"Installed my stuff"', 'None')}
        client.save(files)
        client.run("export . user/testing")
        client.run("install Test/0.1@user/testing --build missing")
        self.assertIn("*+Running system requirements+*", client.user_io.out)
        ref = ConanFileReference.loads("Test/0.1@user/testing")
        self.assertFalse(os.path.exists(client.cache.system_reqs(ref)))
        pref = PackageReference(ref, "f0ba3ca2c218df4a877080ba99b65834b9413798")
        load_file = load(client.cache.system_reqs_package(pref))
        self.assertEqual('', load_file)
