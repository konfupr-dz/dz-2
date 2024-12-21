import unittest
import os
import configparser
import subprocess
from unittest.mock import patch, MagicMock
from main import load_configuration, parse_dependencies, render_uml_diagram


class TestDependencyParser(unittest.TestCase):

    def setUp(self):
        self.config_file = 'config.ini'
        self.package_url = 'https://www.nuget.org/packages/Newtonsoft.Json'
        self.plantuml_path = 'plantuml.jar'
        self.max_depth = 1
        self.create_test_config(self.config_file)

    def create_test_config(self, config_file_path):
        config = configparser.ConfigParser()
        config['Configuration'] = {
            'PlantUMLPath': self.plantuml_path,
            'PackagePath': self.package_url,
            'MaxDepth': str(self.max_depth)
        }
        with open(config_file_path, 'w') as configfile:
            config.write(configfile)

    def test_load_configuration(self):
        plantuml_path, package_url, max_depth = load_configuration(self.config_file)
        self.assertEqual(plantuml_path, self.plantuml_path)
        self.assertEqual(package_url, self.package_url)
        self.assertEqual(max_depth, self.max_depth)

    @patch('requests.get')
    def test_parse_dependencies(self, mock_get):
        # Имитация успешного ответа от сервера
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <span class="title">Newtonsoft.Json</span>
        <span class="version-title">13.0.1</span>
        <ul id="dependency-groups">
            <li>
                <h4><span>Dependencies</span></h4>
                <ul>
                    <li><a href="/packages/SomeDependency">SomeDependency</a> <span>1.0.0</span></li>
                </ul>
            </li>
        </ul>
        </html>
        """
        mock_get.return_value = mock_response

        main_package_name, main_package_version, all_dependencies = parse_dependencies(self.package_url, self.max_depth)

        self.assertEqual(main_package_name, 'Newtonsoft.Json')
        self.assertEqual(main_package_version, '13.0.1')
        self.assertIn('Dependencies', all_dependencies)
        self.assertIn(('SomeDependency', '1.0.0'), all_dependencies['Dependencies'])

    @patch('subprocess.run')
    def test_render_uml_diagram(self, mock_run):
        main_package_name = 'Newtonsoft.Json'
        main_package_version = '13.0.1'
        all_dependencies = {
            'Dependencies': {('SomeDependency', '1.0.0')}
        }

        render_uml_diagram(main_package_name, main_package_version, all_dependencies, self.plantuml_path)

        # Проверяем, что файл записан
        self.assertTrue(os.path.isfile('dependencies.puml'))

        # Проверяем содержание файла
        with open('dependencies.puml') as uml_file:
            uml_content = uml_file.read()
            self.assertIn(main_package_name, uml_content)
            self.assertIn(main_package_version, uml_content)
            self.assertIn('SomeDependency', uml_content)

        # Проверяем вызов subprocess.run
        mock_run.assert_called_once_with(['java', '-jar', self.plantuml_path, 'dependencies.puml'])

    def tearDown(self):
        # Удаление временных файлов после тестов
        files_to_remove = [self.config_file, 'dependencies.puml']
        for file in files_to_remove:
            if os.path.exists(file):
                os.remove(file)


if __name__ == '__main__':
    unittest.main()
