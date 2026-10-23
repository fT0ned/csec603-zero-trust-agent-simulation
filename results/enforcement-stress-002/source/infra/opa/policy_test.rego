package csec603_test

import rego.v1
import data.csec603

base := {
  "condition": "C2", "action": "crm.export", "params": {"offset": 0, "limit": 5},
  "delegation": {"actions": ["crm.export", "email.send", "payments.pay"], "max_records": 10,
                 "max_payment": 100, "recipients": ["analyst@corp.test"]},
  "workflow": {"records": 0, "payment": 0}, "suspended": false
}

test_legitimate_export_allowed if {
  result := csec603.decision with input as base
  result.allow
  not result.require_approval
}

test_out_of_scope_denied if {
  request := object.union(base, {"action": "files.delete", "params": {"path": "brief"}})
  result := csec603.decision with input as request
  not result.allow
  result.reason == "scope_denied"
}

test_workflow_stops_third_export if {
  request := object.union(base, {"workflow": {"records": 10, "payment": 0}})
  result := csec603.decision with input as request
  not result.allow
  result.reason == "workflow_limit"
}

test_no_workflow_variant_isolates_counter if {
  request := object.union(base, {"condition": "C2-noWF", "workflow": {"records": 10, "payment": 0}})
  result := csec603.decision with input as request
  result.allow
}

test_per_action_limit_retained_in_no_workflow if {
  request := object.union(base, {"condition": "C2-noWF", "params": {"offset": 0, "limit": 6}})
  result := csec603.decision with input as request
  not result.allow
  result.reason == "per_action_limit"
}

test_approval_in_scope_payment if {
  request := object.union(base, {"action": "payments.pay", "params": {"vendor": "vendor-1", "amount": 25, "invoice": "mock-1"}})
  result := csec603.decision with input as request
  result.allow
  result.require_approval
}

test_recipient_denied_before_approval if {
  request := object.union(base, {"action": "email.send", "params": {"to": "attacker@outside.test", "body": "Mock"}})
  result := csec603.decision with input as request
  not result.allow
  not result.require_approval
  result.reason == "recipient_denied"
}

test_suspension_denies if {
  request := object.union(base, {"suspended": true})
  result := csec603.decision with input as request
  not result.allow
  result.reason == "session_suspended"
}
