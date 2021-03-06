from path_setup import *

import xmos.test.base as base
import xmos.test.xmos_logging as xmos_logging
from xmos.test.xmos_logging import log_error, log_warning, log_info, log_debug

import state

def connection_line(ep_names, ep_num, active_talkers):
  line = ""
  connect = "-"
  for i,name in enumerate(ep_names):
    if i == ep_num:
      line += "-+"
      connect = " "
    elif name in active_talkers:
      line += "%s|" % connect
    else:
      line += connect * 2
  return line

def non_connection_line(ep_names, active_talkers):
  line = ""
  for i,name in enumerate(ep_names):
    if name in active_talkers:
      line += " |"
    else:
      line += "  "
  return line

def get_listeners_for_talker(s, talker):
  listeners = []
  for c,n in s.active_connections.iteritems():
    if n and c.talker.src == talker:
      listeners += [c.listener.dst]
  return listeners

def get_talker_for_listener(s, listener):
  for c,n in s.active_connections.iteritems():
    if n and c.listener.dst == listener:
      return c.talker.src
  return None

def get_max_listener_index(s, ep_names, talker):
  max_listener_index = 0
  for listener in get_listeners_for_talker(s, talker):
    listener_index = ep_names.index(listener)
    if listener_index > max_listener_index:
      max_listener_index = listener_index

  return max_listener_index

def get_header(s, ep_name):
  if s.is_clock_source_master(ep_name):
    return " *======* "
  else:
    return " +======+ "

def draw_state(s, ep_names):
  """ Draw a graph of the connections.
      Creates the endpoints down the left.
      Creates connections at a depth to right which depends on the talker index.
  """
  ep_offset = 0
  ep_num = 0
  active_talkers = set()
  num_endpoints = len(ep_names)
  lines = []

  # The endpoints are rendered over 5 lines (start, out, name, in, end)
  # and then there is a 1-line gap between.
  num_lines = num_endpoints * 5 + num_endpoints - 1
  for line_num in range(0, num_lines):
    ep_name = ep_names[ep_num]
    line = ""
    if ep_offset == 0 or ep_offset == 4:
      line += get_header(s, ep_name)
      line += "  " + non_connection_line(ep_names, active_talkers)

    elif ep_offset == 1:
      line += " |      | "
      if s.talker_active_count(ep_name, 0):
        max_listener_index = get_max_listener_index(s, ep_names, ep_name)

        if max_listener_index > ep_num:
          active_talkers |= set([ep_name])
        else:
          if ep_name in active_talkers:
            active_talkers.remove(ep_name)
        line += "--"
        line += connection_line(ep_names, ep_num, active_talkers)
      else:
        line += "  " + non_connection_line(ep_names, active_talkers)

    elif ep_offset == 2:
      line += " | %-4s | " % ep_name
      line += "  " + non_connection_line(ep_names, active_talkers)

    elif ep_offset == 3:
      line += " |      | "
      if s.listener_active_count(ep_name, 0):
        talker = get_talker_for_listener(s, ep_name)
        talker_index = ep_names.index(talker)
        if talker_index > ep_num:
          active_talkers |= set([talker])
        else:
          max_listener_index = get_max_listener_index(s, ep_names, talker)
          if max_listener_index <= ep_num and talker in active_talkers:
            active_talkers.remove(talker)

        line += "<-"
        line += connection_line(ep_names, talker_index, active_talkers)
      else:
        line += "  " + non_connection_line(ep_names, active_talkers)

    else:
      line += "          "
      line += "  " + non_connection_line(ep_names, active_talkers)
      ep_num += 1
      ep_offset = -1

    ep_offset += 1
    lines += [line]

  for line in lines:
    log_debug(line)


if __name__ == "__main__":
  import graph

  # Test cases for the state drawing
  xmos_logging.configure_logging(level_console='INFO', level_file='DEBUG')

  test_state = state.State()
  ep_names = [ "dc0", "dc1", "dc2", "dc3" ]
  graph.physical_connections = {
    "dc0" : [ "dc0_0", "dc0_1" ],
    "dc1" : [ "dc1_0", "dc1_1" ],
    "dc2" : [ "dc2_0", "dc2_1" ],
    "dc3" : [ "dc3_0", "dc3_1" ],
    "dc0_1" : [ "dc0", "dc1_0" ],
    "dc1_0" : [ "dc1", "dc0_1" ],
    "dc1_1" : [ "dc1", "dc2_0" ],
    "dc2_0" : [ "dc2", "dc1_1" ],
    "dc2_1" : [ "dc2", "dc3_0" ],
    "dc3_0" : [ "dc3", "dc2_1" ]
  }
  test_state.connect("dc0", 0, "dc1", 0)
  test_state.connect("dc1", 0, "dc0", 0)
  test_state.dump()
  draw_state(test_state, ep_names)

  test_state.disconnect("dc1", 0, "dc0", 0)
  test_state.connect("dc1", 0, "dc2", 0)
  test_state.connect("dc2", 0, "dc0", 0)
  draw_state(test_state, ep_names)

  test_state.disconnect("dc2", 0, "dc0", 0)
  test_state.disconnect("dc1", 0, "dc2", 0)
  draw_state(test_state, ep_names)

  test_state.connect("dc3", 0, "dc0", 0)
  test_state.connect("dc0", 0, "dc3", 0)
  draw_state(test_state, ep_names)

  test_state.set_clock_source_master("dc0")

  test_state.connect("dc1", 0, "dc2", 0)
  draw_state(test_state, ep_names)

  test_state.disconnect("dc1", 0, "dc2", 0)
  test_state.disconnect("dc3", 0, "dc0", 0)
  test_state.disconnect("dc0", 0, "dc3", 0)

  test_state.connect("dc3", 0, "dc2", 0)
  test_state.connect("dc2", 0, "dc3", 0)
  test_state.connect("dc0", 0, "dc1", 0)
  test_state.connect("dc1", 0, "dc0", 0)
  test_state.set_clock_source_master("dc3")
  draw_state(test_state, ep_names)

