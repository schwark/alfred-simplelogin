# encoding: utf-8

import sys
import re
import argparse
from os import listdir, environ
from simplelogin import SimpleLogin
from workflow.workflow import MATCH_ATOM, MATCH_STARTSWITH, MATCH_SUBSTRING, MATCH_ALL, MATCH_INITIALS, MATCH_CAPITALS, MATCH_INITIALS_STARTSWITH, MATCH_INITIALS_CONTAIN
from workflow import Workflow, ICON_WEB, ICON_NOTE, ICON_BURN, ICON_ERROR, ICON_SWITCH, ICON_HOME, ICON_COLOR, ICON_INFO, ICON_SYNC, web, PasswordNotFound
import subprocess 
import urllib.request
from urllib.error import URLError
from common import get_email_domain

log = None


def alias_contact_new(result, wf, id):
    if result and "reverse_alias" in result:
        copy_to_clipboard(result['reverse_alias'])
        return result['reverse_alias']+" in clipboard"
    return None

def update_contacts(fresh, wf):
    stored = wf.cached_data('contact', max_age=0)
    ids = list(map(lambda x: x['id'], fresh))
    stored = list(filter(lambda x: x['id'] not in ids, stored)) if ids else stored
    stored.extend(fresh)      
    wf.cache_data('contact', stored)        

def alias_upcontact(result, wf, id):
    if result:
        one = get_alias(wf, int(id))
        name = one['email'] if one else 'Unknown Alias'
        contacts = list(map(lambda x: post_process_item(wf, x, name), result))
        update_contacts(contacts, wf)
        return "Contacts updated for "+name
    return None

def qnotify(title, text):
    log.debug("notifying..."+text)
    print(text)

def error(text):
    print(text)
    exit(0)

def copy_to_clipboard(text):
    subprocess.run("/usr/bin/pbcopy", text=True, input=text)

def get_notify_name(wf, args):
    type = args['command_type'] 
    #log.debug('type in notify is '+type)
    idkey = 'id'
    name = ''
    if not args[idkey]: return name
    items = wf.cached_data(type, max_age=0)
    #log.debug('items in notify is '+str(items))
    if items:
        item = next((x for x in items if str(args[idkey]) == str(x[idkey])), None)
        name = item['email'] if 'email' in item else (item['contact'] if 'contact' in item else 'item')
        name = ' '.join(map(lambda x: x.capitalize(), re.split('[\.\s\-\,]+', name)))
    return name

def get_alias(wf, id):
    aliases = wf.cached_data('alias', max_age=0)
    return next((x for x in aliases if id == x['id']), None)

def get_client(wf, client_mac):
    clients = wf.cached_data('client', max_age=0)
    return next((x for x in clients if client_mac == x['mac']), None)

def get_device(wf, device_mac):
    devices = wf.cached_data('device', max_age=0)
    return next((x for x in devices if device_mac == x['mac']), None)

def download_icon(wf, contact):
    name, toplevel = get_email_domain(contact['contact'])
    if not name:
        return None
    filename = wf.cachefile(name+".png")
    domain = name+'.'+toplevel
    try:
        urllib.request.urlretrieve('https://www.google.com/s2/favicons?domain='+domain+'&sz=128', filename)
    except URLError:
        log.info('no icon found for '+domain)
        return None
    return filename

def get_hub(wf):
    need_setup = False
    hub = None
    try:
        apikey = wf.get_password('simplelogin_apikey')
    except PasswordNotFound:  
        wf.add_item('No API key found...',
                    'Please use sl api to set your API key...',
                    valid=False,
                    icon=ICON_ERROR)
        need_setup = True
    if need_setup:
        wf.send_feedback()
        exit(0)
    else:
        hub = SimpleLogin(apikey=apikey)
    return hub

def get_aliases(wf, hub):
    """Retrieve all aliases

    Returns a list of aliases.

    """
    return hub.get_aliases()

def get_mailboxes(wf, hub):
    """Retrieve all mailboxes

    Returns a list of mailboxes.

    """
    return hub.get_mailboxes()

def get_domains(wf, hub):
    """Retrieve all domains

    Returns a list of domains.

    """
    return hub.get_domains()

def get_contacts(wf, hub, aliases):
    """Retrieve all contacts

    Returns a list of contacts.

    """
    return hub.get_contacts(aliases)

def call_function(func_name, *args):
    # Attempt to fetch the function from local scope
    func = locals().get(func_name)
    if not func:
        # Attempt to fetch from global scope
        func = globals().get(func_name)
    if func:
        return func(*args)
    return None

def post_process(wf, hub, args, result):
    if not args.command_type or not args.id or not args.command:
        return 
    call = args.command_type+'_'+args.command
    
def handle_commands(wf, hub, args):
    if not args.command_type or not args.id or not args.command:
        return 
    call = args.command_type+'_'+args.command
    params = {"param": args.command_params} if args.command_params else {}
    result = hub.call_dynamic(call, id=args.id, **params)
    message = call_function(call, result, wf, args.id)
    log.debug("type of result is "+str(type(result))+" and result is "+str(result))
    notify_command = re.sub(r'^(fw|pf)', '', args.command)
    notify_command = re.sub(r'e$','',notify_command)
    message = get_notify_name(wf, vars(args))+' '+notify_command+'ed ' if not message else message
    if not result or type(result) is not str:
        qnotify("SimpleLogin", message)
    else:
        qnotify("SimpleLogin", get_notify_name(wf, vars(args))+' '+notify_command+' error: '+result)        
    return result

def get_name(item):
    type = get_item_type(item)
    names = { 'domain': 'suffix', 'alias': 'email', 'mailbox': 'email', 'contact': 'contact'}
    result = item[names[type]] if type in names and names[type] in item else ''
    return result

def  beautify(name):
    if not name:
        return ''
    name = re.sub('^@', '', name)
    return name

def get_item_icon(wf, item):
    type = get_item_type(item)
    filename = download_icon(wf, item) if 'contact' == type else None
    filename = 'icons/'+type+'.png' if not filename else filename
    return filename

def get_item_type(item):
    if 'disable_pgp' in item:
        return 'alias'
    if 'is_premium' in item:
        return 'domain'
    if 'nb_alias' in item:
        return 'mailbox'
    if 'reverse_alias' in item:
        return 'contact'
    return 'alias'

def post_process_item(wf, item, name=None):
    #log.debug("post processing "+str(item))
    item['_display_name'] = beautify(get_name(item))
    item['_type'] = get_item_type(item)
    item['_icon'] = get_item_icon(wf, item)
    if name: item['alias'] = name
    return item

def handle_update(wf, args, hub):
    # Update clients if that is passed in
    if args.update or args.exupdate:  
        # update clients and devices
        aliases = list(map(lambda x: post_process_item(wf, x), get_aliases(wf, hub)))
        domains = list(map(lambda x: post_process_item(wf, x), get_domains(wf, hub)))
        mailboxes = list(map(lambda x: post_process_item(wf, x), get_mailboxes(wf, hub)))
        if aliases:
            wf.cache_data('alias', aliases)
        if domains:
            wf.cache_data('domain', domains)
        if mailboxes:
            wf.cache_data('mailbox', mailboxes)
        if aliases:
            qnotify('SimpleLogin', 'aliases and domains updated')
        else:
            qnotify('SimpleLogin', 'aliases and domains update failed')
    if args.exupdate:
        contacts = list(map(lambda x: post_process_item(wf, x), get_contacts(wf, hub, aliases)))
        if contacts:
            wf.cache_data('contact', contacts)        
        return True # 0 means script exited cleanly

def handle_config_commands(wf, args):
    result = False
    # Reinitialize if necessary
    if args.reinit:
        wf.reset()
        try:
            wf.delete_password('simplelogin_apikey')
        except PasswordNotFound:
            None
        qnotify('SimpleLogin', 'Workflow reinitialized')
        return True

    if args.freq:
        log.debug('saving freq '+args.freq)
        wf.settings['simplelogin_freq'] = int(args.freq)
        wf.settings.save()
        qnotify('SimpleLogin', 'Update Frequency Saved')
        return True

    # save username and password if that is passed in
    if args.api:  
        log.debug("saving API key... ")
        # save the key
        if args.api:
           wf.save_password('simplelogin_apikey', args.api)
        qnotify('SimpleLogin', 'API key Saved')
        return True  # 0 means script exited cleanly
    
def handle_copy_command(wf, args):
    if args.command == 'clip':
        text = ' '.join(args.command_params)
        copy_to_clipboard(text)
        qnotify('Copy to Clipboard', 'Copied to Clipboard '+text)
        return True

def main(wf):
    # build argument parser to parse script args and collect their
    # values
    parser = argparse.ArgumentParser()
    # add an optional (nargs='?') --apikey argument and save its
    # value to 'apikey' (dest). This will be called from a separate "Run Script"
    # action with the API key
    parser.add_argument('--api', dest='api', nargs='?', default=None)
    parser.add_argument('--freq', dest='freq', nargs='?', default=None)
    # add an optional (nargs='?') --update argument and save its
    # value to 'apikey' (dest). This will be called from a separate "Run Script"
    # action with the API key
    parser.add_argument('--update', dest='update', action='store_true', default=False)
    parser.add_argument('--exupdate', dest='exupdate', action='store_true', default=False)
    # reinitialize 
    parser.add_argument('--reinit', dest='reinit', action='store_true', default=False)
    # client name, mac, command and any command params
    parser.add_argument('--command', dest='command', default='')
    parser.add_argument('--command-type', dest='command_type', default='alias')
    parser.add_argument('--command-params', dest='command_params', nargs='*', default=[])

    parser.add_argument('--id', dest='id', default=None)

    # add an optional query and save it to 'query'
    parser.add_argument('query', nargs='?', default=None)
    # parse the script's arguments
    args = parser.parse_args(wf.args)
    log.debug("args are "+str(args))

    if(not handle_config_commands(wf, args)):
        hub = get_hub(wf)
        # handle any cache updates
        handle_update(wf, args, hub)
        # handle copy to clipboard
        if not handle_copy_command(wf, args):
            # handle any client or device commands there may be
            handle_commands(wf, hub, args)
    return 0


if __name__ == u"__main__":
    wf = Workflow(update_settings={
        'github_slug': 'schwark/alfred-simplelogin'
    })
    log = wf.logger
    sys.exit(wf.run(main))
    