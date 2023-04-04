import ast
import os
import sys

from conan.api.conan_api import ConanAPI
from conan.api.model import ListPattern
from conan.api.output import ConanOutput
from conan.cli.command import conan_command


@conan_command(group="Extension")
def bump_reqs(conan_api: ConanAPI, parser, *args):
    """
    command bumping all requirements of a recipe
    """
    parser.add_argument("recipe", help="Recipe for which the requirements will be bumped", default="conanfile.py")
    parser.add_argument("--remote", "-r", help="Name of the remote providing new versions", default="*")
    args = parser.parse_args(*args)
    recipe_file = args.recipe

    if not os.path.isfile(recipe_file):
        ConanOutput().error(f"Recipe file {recipe_file} not found")
        sys.exit(-1)

    with open(recipe_file) as f:
        recipe = f.read()
        f.seek(0)
        recipe_lines = f.readlines()

    for node in ast.walk(ast.parse(recipe)):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ["requires", "build_requires", "tool_requires"]:
                    arg = node.args[0]
                    if not isinstance(arg, ast.Constant):
                        ConanOutput().warning(f"Unable to bump non constant requirement in {recipe_file}:{arg.lineno}")
                        continue
                    oldref = arg.value
                    name = oldref.split("/")[0]
                    try:
                        refs = conan_api.list.select(ListPattern(name), remote=conan_api.remotes.list(args.remote)[0])
                    except Exception as inst:
                        ConanOutput().warning(f"Error bumping {oldref} in {recipe_file}:{arg.lineno}")
                        ConanOutput().warning(inst)
                        continue
                    newref = list(refs.recipes.keys())[-1]
                    if newref != oldref:
                        line = arg.lineno - 1
                        recipe_lines[line] = recipe_lines[line].replace(oldref, newref)
                        ConanOutput().info(f"updating {oldref} to {newref} in {recipe_file}:{arg.lineno}")

    with open(recipe_file, 'w') as f:
        f.writelines(recipe_lines)

    ConanOutput().success(f"Successfully bumped the requirements of recipe {recipe_file}")
