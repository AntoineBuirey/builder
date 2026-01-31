import cmd
from gamuLogger import Logger
from .project import Project


class InteractiveShell(cmd.Cmd):
    """Interactive shell for running build rules."""
    
    intro = """
    ╔═══════════════════════════════════════════════╗
    ║  Builder Interactive Shell                    ║
    ║  Type 'help' for available commands           ║
    ╚═══════════════════════════════════════════════╝
    """
    prompt = "builder> "
    
    def __init__(self, project: Project):
        """Initialize the interactive shell.
        
        Args:
            project: The Project instance
            rules: List of selected Rule instances to execute
        """
        super().__init__()
        self.project = project
        self.rules_dict = project.get_all_rules()
    
    def do_list(self, arg):
        """List all available rules. Usage: list"""
        if not self.project.get_all_rules():
            print("No rules available.")
            return
        
        print(f"\n{'Rule Name':<30} {'Tags':<30} {'Commands':<10}")
        print("-" * 70)
        for name, rule in self.project.get_all_rules().items():
            tags_str = ', '.join(rule.tags) if rule.tags else '-'
            print(f"{name:<30} {tags_str:<30} {len(rule.commands):<10}")
    
    def do_run(self, arg):
        """Run one or more rules. Usage: run <rule_name> [rule_name2 ...]
        
        Examples:
            run build          - Run the 'build' rule
            run test compile   - Run 'test' and 'compile' rules
        """
        if not arg:
            Logger.warning("Please specify one or more rule names. Usage: run <rule_name> [rule_name2 ...]")
            return
        
        rule_names = arg.split()
        
        for rule_name in rule_names:
            if rule_name not in self.rules_dict:
                print(f"\033[31mRule not found: {rule_name}\033[0m")
                print("Available rules: " + ', '.join(self.rules_dict.keys()))
                return
        
        try:
            for rule_name in rule_names:
                rule = self.rules_dict[rule_name]
                print(f"Running rule: {rule_name}")
                rule.execute()
        except Exception as e:
            Logger.fatal(f"Failed to execute rule: {e}")
    
    def do_info(self, arg):
        """Show detailed information about a rule. Usage: info <rule_name>"""
        if not arg:
            Logger.warning("Please specify a rule name. Usage: info <rule_name>")
            return
        
        rule_name = arg.strip()
        
        if rule_name not in self.rules_dict:
            print(f"\033[31mRule not found: {rule_name}\033[0m")
            print("Available rules: " + ', '.join(self.rules_dict.keys()))
            return
        
        rule = self.rules_dict[rule_name]
        print("\n" + rule.get_summary())
    
    def do_vars(self, arg):
        """Show project variables. Usage: vars [var_name]"""
        if not arg:
            print("\nProject Variables:")
            print("-" * 50)
            for key, value in self.project.get_all_vars().items():
                if isinstance(value, (str, int, float, bool)):
                    print(f"{key:<30} = {value}")
                else:
                    print(f"{key:<30} = {type(value).__name__} object")
        else:
            var_name = arg.strip()
            if var_name in self.project.vars:
                value = self.project.vars[var_name]
                print(f"{var_name} = {value}")
            else:
                print(f"\033[31mVariable not found: {var_name}\033[0m")
                print("Available variables: " + ', '.join(self.project.vars.keys()))
        print()
    
    def do_summary(self, arg):
        """Show project summary. Usage: summary"""
        print("\n" + self.project.get_summary())
    
    def do_exit(self, arg):
        """Exit the interactive shell. Usage: exit"""
        print("Goodbye!")
        return True
    
    def do_quit(self, arg):
        """Quit the interactive shell. Usage: quit"""
        return self.do_exit(arg)
    
    def default(self, line):
        """Handle unknown commands."""
        if line in ('EOF', 'q'):
            self.do_exit(line)
        print(f"\033[31mUnknown command: {line}\033[0m")
        print("Type 'help' for available commands.")
    
    def emptyline(self):
        """Handle empty line input."""
        return False