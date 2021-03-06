#!/usr/bin/env python
"""The auditing system."""


import os

from grr.lib import flags
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import events
from grr.server.flows.general import audit
from grr.server.flows.general import filesystem
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class TestAuditSystem(flow_test_lib.FlowTestsBaseclass):

  def testFlowExecution(self):
    client_mock = action_mocks.ListDirectoryClientMock()

    rollover = aff4.AUDIT_ROLLOVER_TIME.seconds
    # Set time to epoch + 20 intervals
    with test_lib.FakeTime(20 * rollover):
      for _ in flow_test_lib.TestFlowHelper(
          filesystem.ListDirectory.__name__,
          client_mock,
          client_id=self.client_id,
          pathspec=rdf_paths.PathSpec(
              path=os.path.join(self.base_path, "test_img.dd/test directory"),
              pathtype=rdf_paths.PathSpec.PathType.OS),
          token=self.token):
        pass

      for _ in flow_test_lib.TestFlowHelper(
          filesystem.ListDirectory.__name__,
          client_mock,
          client_id=self.client_id,
          pathspec=rdf_paths.PathSpec(
              path=os.path.join(self.base_path, "test_img.dd/test directory"),
              pathtype=rdf_paths.PathSpec.PathType.OS),
          token=self.token):
        pass

      parentdir = aff4.FACTORY.Open(
          "aff4:/audit/logs", aff4.AFF4Volume, mode="r", token=self.token)

      logs = list(parentdir.ListChildren())
      self.assertEqual(len(logs), 1)
      log = aff4.CurrentAuditLog()
      stored_events = audit.AuditEventCollection(log, token=self.token)

      self.assertEqual(len(stored_events), 2)
      for event in stored_events:
        self.assertEqual(event.action, events.AuditEvent.Action.RUN_FLOW)
        self.assertEqual(event.flow_name, filesystem.ListDirectory.__name__)
        self.assertEqual(event.user, self.token.username)

    # Set time to epoch + 22 intervals
    with test_lib.FakeTime(22 * rollover):
      for _ in flow_test_lib.TestFlowHelper(
          filesystem.ListDirectory.__name__,
          client_mock,
          client_id=self.client_id,
          pathspec=rdf_paths.PathSpec(
              path=os.path.join(self.base_path, "test_img.dd/test directory"),
              pathtype=rdf_paths.PathSpec.PathType.OS),
          token=self.token):
        pass

      parentdir = aff4.FACTORY.Open(
          "aff4:/audit/logs", aff4.AFF4Volume, mode="r", token=self.token)
      # Now we should have two collections
      logs = list(parentdir.ListChildren())
      self.assertEqual(len(logs), 2)

      # One with two events
      stored_events = audit.AuditEventCollection(logs[0], token=self.token)
      self.assertEqual(len(stored_events), 2)

      # The other with one
      stored_events = audit.AuditEventCollection(logs[1], token=self.token)
      self.assertEqual(len(stored_events), 1)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
