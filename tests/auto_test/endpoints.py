import sys
import time
import os

from twisted.internet import reactor, defer

import xmos.test.process as process
import xmos.test.master as master
import xmos.test.base as base
from xmos.test.xmos_logging import log_error, log_warning, log_info, log_debug

import analyzers

all_endpoints = {}

def get_all():
  return all_endpoints

def get(name):
  """ Get an endpoint given the name of it.
  """
  return all_endpoints.get(name, None)

def get_path_endpoints(path):
  """ Given a path, find any endpoints between the start and end endpoints. This
      means excluding nodes which are the ports.
  """
  if path is None or len(path) < 2:
    return []

  nodes = []
  for node in path[1:-1]:
    if get(node):
      nodes.append(node)
  return nodes

def get_avb_id(user, ep):
    user_config = ep['users'][user]
    return user_config['avb_id']

def guid_in_ascii(user, ep):
  return get_avb_id(user, ep).encode('ascii', 'ignore')

def mac_byte_str(mac_str, i):
  index = len(mac_str) - ((i + 1) * 2)
  if index < 0:
    return "0"
  sub_str = mac_str[index:index+2]
  sub_str = sub_str.lstrip('0')
  if sub_str:
    return sub_str.upper()
  else:
    return "0"

def mac_in_ascii(user, ep):
  avb_id = guid_in_ascii(user, ep).encode('ascii', 'ignore')
  mac_strs = []
  indexes = range(0,8)
  indexes.reverse()
  for i in indexes:
    mac_strs += [mac_byte_str(avb_id, i)]
  return ":".join(mac_strs)

def stream_from_guid(guid):
  return guid[0:4].upper() + guid[-6:].upper() + "0000"

def determine_grandmaster(user):
  """ From the endpoints described determine which will be the grandmaster.
      It is the node with the lowest MAC address unless there is a switch
      which has a different priority.
  """
  grandmaster = None
  for name,ep in all_endpoints.iteritems():
    if not grandmaster:
      grandmaster = ep
    else:
      e_id = get_avb_id(user, ep)
      if e_id < get_avb_id(user, grandmaster):
        grandmaster = ep
  return grandmaster

def startXrun(combined_args):
  (name, process, adapter_id, bin, args) = combined_args

  # Windows requires the absolute path of xrun
  exe_name = base.exe_name('xrun')
  xrun = base.file_abspath(exe_name)

  log_info("Starting %s (%s)" % (name, ' '.join(['--adapter-id', adapter_id, '--xscope', '--xscope-file',  name + '.xmt', bin])))
  reactor.spawnProcess(process, xrun, [xrun, '--adapter-id', adapter_id, '--xscope', '--xscope-file', name + '.xmt', bin],
      env=os.environ, path=args.logdir)

def startXrunWithDelay(rootDir, master, delay, name, adapter_id, args):
  # Need to ensure that the endpoint and process are created and registered before the
  # master task is started
  ep = process.XrunProcess(name, master,
      output_file=os.path.join(args.logdir, name + '_console.log'))
  ep_bin = os.path.join(rootDir, 'sw_avb_dc', 'app_daisy_chain', 'bin', 'app_daisy_chain.xe')

  log_info("Starting %s in %.3f" % (name, delay))
  d = defer.Deferred()
  reactor.callLater(delay, d.callback, (name, ep, adapter_id, ep_bin, args))
  d.addCallback(startXrun)

def start(rootDir, args, master, endpoints, initial_delay):
  delay = initial_delay
  for ep in endpoints:
    name = ep['name']
    all_endpoints[name] = ep

    if args.user not in ep['users']:
      log_error("User '%s' not found in config file '%s' for endpoint '%s'" %
          (args.user, args.config, name))
      sys.exit(1)

    user_config = ep['users'][args.user]
    startXrunWithDelay(rootDir, master, delay, ep['name'], user_config['xrun_adapter_id'], args)

    delay += 2.0

  # Connect up the analyzers to then endpoints
  for ep in endpoints:
    analyzer_name = ep['analyzer']
    if analyzer_name not in analyzers.get_all():
      log_error("Invalid analyzer '%s' for endpoint '%s'" % (analyzer_name, ep['name']))
    ep['analyzer'] = analyzers.get_all()[analyzer_name]

  # Return the delay used so that the next set of processes can be started after these ones
  # to minimize chances of interference
  return delay

