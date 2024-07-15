# alfred-simplelogin
Alfred  Workflow for interacting with SimpleLogin

## Install
* Download .workflow file from [Releases](https://github.com/schwark/alfred-simplelogin/releases)
* Can also be downloaded from github as a zip file, unzip the downloaded zip, cd into the zip directory, and create a new zip with all the files in that folder, and then renamed to Smartthings.alfredworkflow
* Or you can use the workflow-build script in the folder, using
```
chmod +x workflow-build
./workflow-build . 
```

## Credentials

```
sl api <apikey>
```
This should only be needed once per install or after a reinit - stored securely in MacOS keychain


## Device/Client/Icons Update

```
sl update
```
This should be needed once at the install, and everytime you want to refresh information on aliases, domains and mailboxes - should happen automatically at least once a month - this takes quite a while to complete - upto 1-2 minutes depending on the number of contacts

```
sl exupdate
```
This should be needed once at the install, and everytime you want to refresh information on contacts as well as aliases, domains and mailboxes - this takes a very long while to complete - upto 5-10 minutes depending on the number of contacts

## Alias Commands

```
sl <alias-name> clip|toggle|enable|disable|delete|update|contact <email address>
```

* clip - copies the name to clipboard
* toggle - reverses the enabled/disabled
* enable - turns on irrespective of current state
* disable - turns off irrespective of current state
* delete - deletes the alias
* update - updates the contacts for this alias
* contact - create new contact for this alias with this email address - the reverse address will be saved to clipboard


## Contact Commands

```
sl <contact-name> clip|toggle|enable|disable|delete
```

* clip - copies the name to clipboard
* toggle - reverses the enabled/disabled
* enable - turns on irrespective of current state
* disable - turns off irrespective of current state
* delete - deletes the alias


## Mailbox Commands

```
sl <mailbox-name> clip
```

* clip - copies the name to clipboard


## Update Frequency

```
sl freq <number-of-seconds>
```
This is an optional setting to change how frequently the clients and their status is updated. This takes a couple of seconds and so making it too small may be annoying, but it is a tradeoff between fresh data and speed of response. By default, this is updated once a day. A more aggressive but still usable setting is 3600 or every hour.

## Reinitialize

```
sl reinit
```
This should only be needed if you ever want to start again for whatever reason - removes all API keys, devices, scenes, etc.

## Update

```
sl workflow:update
```
An update notification should show up when an update is available, but if not invoking this should update the workflow to latest version on github

## Acknowledgements

Icons made by [Freepik](https://www.flaticon.com/authors/freepik) from [www.flaticon.com](https://www.flaticon.com)  
