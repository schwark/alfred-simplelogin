import re

def get_email_domain(email):
    domain = re.search('([^\.@]+)\.(co\.\w{2}|com|org|net)', email)
    if not domain:
        return None, None
    toplevel = domain[2]
    name = domain[1].replace('-mail','')
    return name, toplevel
