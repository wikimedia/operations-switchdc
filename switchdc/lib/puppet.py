def get_agent_run_command():
    """Return a puppet agent run command equivalent to --test without --detailed-exitcodes."""
    return 'puppet agent -ov --ignorecache --no-daemonize --no-usecacheonfailure --no-splay --show_diff'
