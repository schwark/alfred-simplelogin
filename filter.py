# encoding: utf-8

import sys
import re
import argparse
from workflow.workflow import MATCH_ATOM, MATCH_STARTSWITH, MATCH_SUBSTRING, MATCH_ALL, MATCH_INITIALS, MATCH_CAPITALS, MATCH_INITIALS_STARTSWITH, MATCH_INITIALS_CONTAIN
from workflow import Workflow, ICON_WEB, ICON_NOTE, ICON_BURN, ICON_ERROR, ICON_SWITCH, ICON_HOME, ICON_COLOR, ICON_INFO, ICON_SYNC, web, PasswordNotFound
from workflow.background import run_in_background, is_running
from common import get_email_domain

log = None

def error(text):
    print(text)
    exit(0)

def get_uptime(secs):
    if secs < 60:
        return str(secs)+' sec'
    if secs < 3600:
        return str(int(secs/60))+' min'
    if secs < 86400:
        return str(int(secs/60/60))+' hrs'
    if secs >= 86400:
        return str(int(secs/60/60/24))+' days'

def get_device_clients(wf, device):
    device_mac = device['mac']
    clients = wf.cached_data('client', max_age=0)
    result = filter(lambda x: ('ap_mac' in x and x['ap_mac'] == device_mac) or ('ap_mac' not in x and 'sw_mac' in x and x['sw_mac'] == device_mac), clients)
    devices = wf.cached_data('device', max_age=0)
    result.extend(filter(lambda x: ('uplink' in x and 'uplink_mac' in x['uplink'] and device_mac == x['uplink']['uplink_mac']), devices))
    return result

def get_item_subtitle(item, type):
    subtitle = u''

    if 'alias' == type:
        if 'enabled' in item:
            subtitle += (u'  👍🏼 '+'enabled' if item['enabled'] else u'  👎 '+'disabled') 
        if 'mailbox' in item:
            subtitle += u'  📧 '+(item['mailbox']['email'] if item['mailbox'] and 'email' in item['mailbox'] and item['mailbox']['email'] else 'none') 
            
    if 'mailbox' == type:
        if 'verified' in item:
            subtitle += u'  ✅ '+('verified' if item['verified'] else 'not verified') 
        if 'default' in item:
            subtitle += u'  🥇 '+('default' if item['default'] else 'secondary') 
            
    if 'domain' == type:
        if 'is_custom' in item:
            subtitle += u'  🎈 '+('custom' if item['is_custom'] else 'standard') 
        if 'is_premium' in item:
            subtitle += u'  💵 '+('premium' if item['is_premium'] else 'standard') 
            
    if 'contact' == type:
        if 'enabled' in item:
            subtitle += (u'  👍🏼 '+'enabled' if item['enabled'] else u'  👎 '+'disabled') 
        if 'alias' in item:
            subtitle += u'  📨 '+(item['alias'] if item['alias'] else 'none') 
        if 'reverse_alias_address' in item:
            subtitle += u'  📧 '+(item['reverse_alias_address'] if item['reverse_alias_address'] else 'none') 

    return subtitle

def search_key_for_alias(alias):
    """Generate a string search key for a client"""
    if not alias:
        return None
    elements = []
    if  'email' in alias:
        elements.append(alias['email'])
        elements.extend(alias['email'].split('@'))  # alias email parts
    if  'latest_activity' in alias and alias['latest_activity'] and \
        'contact' in alias['latest_activity'] and alias['latest_activity']['contact'] and \
        'email' in alias['latest_activity']['contact'] and alias['latest_activity']['contact']['email']:
            #elements.append(alias['latest_activity']['contact']['email'])
            name, toplevel = get_email_domain(alias['latest_activity']['contact']['email'])
            if name:
                elements.append(name)  # sender email domain
    return u' '.join(elements)

def search_key_for_domain(domain):
    """Generate a string search key for a domain"""
    elements = []
    #elements.append(domain['suffix'])
    elements.append(domain['suffix'].split('@')[-1])  # name of domain
    return u' '.join(elements)

def search_key_for_mailbox(mailbox):
    """Generate a string search key for a mailbox"""
    elements = []
    #elements.append(mailbox['email'])
    elements.extend(mailbox['email'].split('@'))  # mailbox parts
    return u' '.join(elements)

def search_key_for_contact(contact):
    """Generate a string search key for a contact"""
    elements = []
    matches = re.search('([^\.]+)@(.*)', contact['contact'])
    elements.append(matches[1])
    elements.append(matches[2])    
    elements.append(contact['contact'])
    return u' '.join(elements)

def add_prereq(wf, args):
    result = False
    word = args.query.lower().split(' ')[0] if args.query else ''
    # check API key
    try:
        apikey = wf.get_password('simplelogin_apikey')
    except PasswordNotFound:  
        if word != 'api':
            wf.add_item('No API key found...',
                        'Please use sl api to set your API key',
                        valid=False,
                        icon=ICON_ERROR)
        result = True
    # check aliases
    aliases = wf.cached_data('alias', max_age=0)
    domains = wf.cached_data('domain', max_age=0)
    mailboxes = wf.cached_data('mailbox', max_age=0)
    if (not aliases or not domains or not mailboxes):
        if word != 'update':
            wf.add_item('No aliases...',
                    'Please use sl update - to update your aliases, domains and mailboxes.',
                    valid=False,
                    icon=ICON_NOTE)
        result = True
    # Check for an update and if available add an item to results
    if wf.update_available:
        # Add a notification to top of Script Filter results
        wf.add_item('New version available',
            'Action this item to install the update',
            autocomplete='workflow:update',
            icon=ICON_INFO)
    return result

def add_config_commands(wf, query, config_commands):
    word = query.lower().split(' ')[0] if query else ''
    config_command_list = wf.filter(word, config_commands.keys(), min_score=80)
    if config_command_list:
        for cmd in config_command_list:
            wf.add_item(config_commands[cmd]['title'],
                        config_commands[cmd]['subtitle'],
                        arg=config_commands[cmd]['args'],
                        autocomplete=config_commands[cmd]['autocomplete'],
                        icon=config_commands[cmd]['icon'],
                        valid=config_commands[cmd]['valid'])
    return config_command_list

def filter_exact_match(query, result):
    if result:
        # check to see if any one is an exact match - if yes, remove all the other results
        for i in range(len(result)):
            name = result[i]['_display_name']
            if name.lower() == query.lower():
                result = [result[i]]
                break
    return result

def get_filtered_items(wf, query, items, search_func):
    result = wf.filter(query, items, key=search_func, min_score=80)
    result = filter_exact_match(query, result)
    return result

def get_id(item):
    if 'mac' in item:
        return item['mac']
    else:
        return item['_id']

def extract_commands(wf, args, clients, filter_func, valid_commands):
    words = args.query.split() if args.query else []
    result = vars(args)
    if clients:
        clients = list(filter(lambda x: x, clients))
        #log.debug("clients are: "+str(clients))
        full_clients = get_filtered_items(wf, args.query,  clients, filter_func)
        minusone_clients = get_filtered_items(wf, ' '.join(words[0:-1]),  clients, filter_func) if len(words) > 1 else []
        minustwo_clients = get_filtered_items(wf, ' '.join(words[0:-2]),  clients, filter_func) if len(words) > 2 else []

        #log.debug('full client '+str(full_clients[0])+', and minus one is '+str(minusone_clients[0]))
        if 1 == len(minusone_clients) and (0 == len(full_clients) or (1 == len(full_clients) and get_id(full_clients[0]) == get_id(minusone_clients[0]))):
            name = minusone_clients[0]['_display_name']
            extra_words = args.query.replace(name,'').split()
            if extra_words and extra_words[0] in valid_commands:
                log.debug("extract_commands: setting command to "+extra_words[0])
                result['command'] = extra_words[0]
                result['query'] = name
        if 1 == len(minustwo_clients) and 0 == len(full_clients) and 0 == len(minusone_clients):
            name = minustwo_clients[0]['_display_name']
            extra_words = args.query.replace(name,'').split()
            if extra_words and extra_words[0] in valid_commands:
                result['command'] = extra_words[0]
                result['query'] = name
                result['params'] = extra_words[1:]
        log.debug("extract_commands: "+str(result))
    return result

def get_valid_commands(items):
    result = []
    for item in items:
        result = result + item['commands']
    return result

def get_device_map(devices):
    return { x['mac'] if x and 'mac' in x else None: x for x in devices } if devices else None

def main(wf):
    # build argument parser to parse script args and collect their
    # values
    parser = argparse.ArgumentParser()
    # add an optional query and save it to 'query'
    parser.add_argument('query', nargs='?', default=None)
    # parse the script's arguments
    args = parser.parse_args(wf.args)
    log.debug("args are "+str(args))

    # update query post extraction
    query = args.query if args.query else ''
    words = query.split(' ') if query else []

    # list of commands
    alias_commands = {
        'clip': {
            'command': 'clip',
            'params': ['email']
        },
        'contact': {
            'command': 'contact_new',
            'params': ['contact']
        },
        'toggle': {
                'command': 'toggle'
        },
        'update': {
                'command': 'upcontact'
        },
        'enable': {
                'command': 'enable'
        },
        'disable': {
                'command': 'disable'
        },
        'delete': {
                'command': 'delete'
        }, 
    }

    mailbox_commands = {
    }

    domain_commands = {
    }
    
    contact_commands = {
        'clip': {
            'command': 'clip',
            'params': ['reverse_alias_address']
        },
        'toggle': {
            'command': 'toggle'
        },
        'enable': {
                'command': 'enable'
        },
        'disable': {
                'command': 'disable'
        },
        'delete': {
            'command': 'delete'
        },
    }

    config_commands = {
        'update': {
            'title': 'Update aliases, domains and mailboxes',
            'subtitle': 'Update the aliases, domains and mailboxes',
            'autocomplete': 'update',
            'args': ' --update',
            'icon': ICON_SYNC,
            'valid': True
        },
        'exupdate': {
            'title': 'Extended update including contacts',
            'subtitle': 'Extended update of everything including contacts',
            'autocomplete': 'exupdate',
            'args': ' --exupdate',
            'icon': ICON_SYNC,
            'valid': True
        },
        'api': {
            'title': 'Set api key',
            'subtitle': 'Set the api key',
            'autocomplete': 'api',
            'args': ' --api '+(words[1] if len(words)>1 else ''),
            'icon': ICON_WEB,
            'valid': len(words) > 1
        },
        'freq': {
            'title': 'Set device and client update frequency',
            'subtitle': 'Every (x) seconds, the clients and stats will be updated',
            'autocomplete': 'freq',
            'args': ' --freq '+(words[1] if len(words)>1 else ''),
            'icon': ICON_WEB,
            'valid': len(words) > 1
        },
        'reinit': {
            'title': 'Reinitialize the workflow',
            'subtitle': 'CAUTION: this deletes all devices, clients and credentials...',
            'autocomplete': 'reinit',
            'args': ' --reinit',
            'icon': ICON_BURN,
            'valid': True
        },
        'workflow:update': {
            'title': 'Update the workflow',
            'subtitle': 'Updates workflow to latest github version',
            'autocomplete': 'workflow:update',
            'args': '',
            'icon': ICON_SYNC,
            'valid': True
        }
    }


    # add config commands to filter
    add_config_commands(wf, query, config_commands)
    if(add_prereq(wf, args)):
        wf.send_feedback()
        return 0
 
    freq = int(wf.settings['simplelogin_freq']) if 'simplelogin_freq' in wf.settings else 86400*30
    # Is cache over 1 month old or non-existent?
    if not wf.cached_data_fresh('alias', freq):
        run_in_background('update',
                        ['/usr/bin/python3',
                        wf.workflowfile('command.py'),
                        '--update'])

    if is_running('update'):
        # Tell Alfred to run the script again every 0.5 seconds
        # until the `update` job is complete (and Alfred is
        # showing results based on the newly-retrieved data)
        wf.rerun = 0.5
        # Add a notification if the script is running
        wf.add_item('Updating aliases, mailboxes and domains...', icon=ICON_INFO)
    # If script was passed a query, use it to filter posts
    elif is_running('exupdate'):
        # Tell Alfred to run the script again every 0.5 seconds
        # until the `update` job is complete (and Alfred is
        # showing results based on the newly-retrieved data)
        wf.rerun = 0.5
        # Add a notification if the script is running
        wf.add_item('Updating contacts, aliases, mailboxes and domains...', icon=ICON_INFO)
    elif query:
        # retrieve cached clients and devices
        aliases = wf.cached_data('alias', max_age=0)
        mailboxes = wf.cached_data('mailbox', max_age=0)
        domains = wf.cached_data('domain', max_age=0)
        contacts = wf.cached_data('contact', max_age=0)

        items = [
            {
                'name': 'aliases',
                'list': aliases,
                'commands': alias_commands,
                'id': 'id',
                'filter': search_key_for_alias
            },
            {
                'name': 'mailboxes',
                'list': mailboxes,
                'commands': mailbox_commands,
                'id': 'id',
                'filter': search_key_for_mailbox
            },
            {
                'name': 'domains',
                'list': domains,
                'commands': domain_commands,
                'id': 'suffix',
                'filter': search_key_for_domain
            },
            {
                'name': 'contacts',
                'list': contacts,
                'commands': contact_commands,
                'id': 'id',
                'filter': search_key_for_contact
            },
        ]
        
        result_items = {}
        total_results = 0
        
        for item in items:
            item['list'] = list(filter(lambda x: x, item['list']))
            parts = extract_commands(wf, args, item['list'], item['filter'], item['commands'])
            query = parts['query']
            item_list = get_filtered_items(wf, query, item['list'], item['filter'])
            result_items[item['name']] = item_list
            total_results = total_results + len(item_list)
        
        for item in items:
            parts = extract_commands(wf, args, item['list'], item['filter'], item['commands'])
            query = parts['query']
            item_list = result_items[item['name']]

            # since this i now sure to be a client/device query, fix args if there is a client/device command in there
            command = parts['command'] if 'command' in parts else ''
            params = parts['params'] if 'params' in parts else [query]

            if item_list:
                if 1 == total_results:
                    # Single client only, no command or not complete command yet so populate with all the commands
                    single = item_list[0]
                    name = single['_display_name']
                    cmd_list = list(filter(lambda x: x.startswith(command), item['commands'].keys())) if (not command or command not in item['commands']) else [command]
                    log.debug('parts.'+single['_type']+'_command is '+command)
                    for command in cmd_list:
                        param_str = str(' '.join(list(map(lambda x: single[x] if x in single else '', item['commands'][command]['params'])))) if command in item['commands'] and 'params' in item['commands'][command] else ''
                        if not param_str:
                            param_str = params if params else ''
                        wf.add_item(title=name,
                                subtitle=command.capitalize()+' '+name,
                                arg=' --'+item['id']+' "'+str(single[item['id']])+'" --command-type '+single['_type']+' --command '+command+' --command-params "'+str(param_str)+'"',
                                autocomplete=name+' '+command,
                                valid=bool('arguments' not in item['commands'][command] or param_str),
                                icon=single['_icon'])
                # Loop through the returned clients and add an item for each to
                # the list of results for Alfred
                for single in item_list:
                    name = single['_display_name']
                    item_type = single['_type']
                    wf.add_item(title=name,
                            subtitle=get_item_subtitle(single, item_type),
                            arg=' --'+item['id']+' "'+str(single[item['id']])+'" --command-type '+item_type+' --command clip --command-params "'+(name if name else '')+'"',
                            autocomplete=name,
                            valid=len(item['commands']) < 2,
                            icon=single['_icon'])

        # Send the results to Alfred as XML
    wf.send_feedback()
    return 0


if __name__ == u"__main__":
    wf = Workflow(update_settings={
        'github_slug': 'schwark/alfred-simplelogin'
    })
    log = wf.logger
    sys.exit(wf.run(main))
    