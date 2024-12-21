import os
import sys
import subprocess
import requests
import configparser
from bs4 import BeautifulSoup


def load_configuration(config_path):
    if not os.path.isfile(config_path):
        raise Exception('Configuration file not found')

    config = configparser.ConfigParser()
    config.read(config_path)

    plantuml_path = config['Configuration'].get('PlantUMLPath', 'plantuml')
    package_url = config['Configuration']['PackagePath']
    max_depth = int(config['Configuration']['MaxDepth'])

    return plantuml_path, package_url, max_depth


def parse_dependencies(package_url, max_depth, depth=1):
    response = requests.get(package_url + '#dependencies-body-tab')
    if response.status_code != 200:
        raise Exception('HTML page parse error')

    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    main_package_name = soup.find('span', {'class': 'title'}).text.strip()
    main_package_version = soup.find('span', {'class': 'version-title'}).text.strip()
    all_dependencies = {}

    dependencies_div = soup.find('ul', {'id': 'dependency-groups'})
    if not dependencies_div:
        return main_package_name, main_package_version, all_dependencies

    dependency_rows = dependencies_div.findAll('li', recursive=False)
    if dependency_rows:
        for dependency_row in dependency_rows:
            dependency_group_name = dependency_row.find('h4').find('span').text.strip()
            dependency_list = dependency_row.find('ul', recursive=False).findAll('li', recursive=False)
            for dependency in dependency_list:
                dependency_name_tag = dependency.find('a')
                if dependency_name_tag:
                    dependency_link = dependency_name_tag.get('href')
                    if dependency_link and depth + 1 <= max_depth:
                        nested_dependencies = parse_dependencies('https://www.nuget.org' + dependency_link, max_depth, depth + 1)[2]
                        all_dependencies.update(nested_dependencies)
                    dependency_name = dependency_name_tag.text.strip()
                    dependency_version = dependency.find('span').text.strip()
                    all_dependencies.setdefault(dependency_group_name, set()).add((dependency_name, dependency_version))

    return main_package_name, main_package_version, all_dependencies


def render_uml_diagram(main_package_name, main_package_version, all_dependencies, plantuml_path):
    uml_content = "@startuml\n"
    uml_content += f'component "{main_package_name}\\n{main_package_version}" as {main_package_name} #lightblue\n'

    for group_name, deps in all_dependencies.items():
        uml_content += f'package "{group_name}" #lightgrey {{\n'
        for dep_name, dep_version in deps:
            uml_content += f'  component "{dep_name}\\n{dep_version}" as {dep_name}\n'
            uml_content += f'  {main_package_name} --> {dep_name}\n'
        uml_content += '}\n'
    uml_content += "@enduml\n"

    with open('dependencies.puml', 'w') as uml_file:
        uml_file.write(uml_content)

    subprocess.run(['java', '-jar', plantuml_path, 'dependencies.puml'])


def main(config_file_path):
    plantuml_path, package_url, max_depth = load_configuration(config_file_path)
    main_package_name, main_package_version, all_dependencies = parse_dependencies(package_url, max_depth)
    render_uml_diagram(main_package_name, main_package_version, all_dependencies, plantuml_path)
    print("Diagram created successfully!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python main.py <config_file_path>')
        sys.exit(1)

    main(sys.argv[1])
