import sys
from argparse import ArgumentParser, _SubParsersAction
from facefusion import program

def validate_actions(program):
    for action in program._actions:
        if action.default and action.choices:
            if isinstance(action.default, list):
                for default in action.default:
                    if default not in action.choices:
                        print(f"FAILED: Action '{action.dest}' has default list {action.default} but choice {default} is not in {action.choices}")
                        return False
            elif action.default not in action.choices:
                print(f"FAILED: Action '{action.dest}' has default {action.default} but it is not in {action.choices}")
                return False
    return True

def validate_args_debug(program):
    if validate_actions(program):
        for action in program._actions:
            if isinstance(action, _SubParsersAction):
                for name, sub_program in action._name_parser_map.items():
                    if not validate_args_debug(sub_program):
                        print(f"FAILED in subprogram: {name}")
                        return False
        return True
    return False

p = program.create_program()
print(f"Final Validation Result: {validate_args_debug(p)}")
