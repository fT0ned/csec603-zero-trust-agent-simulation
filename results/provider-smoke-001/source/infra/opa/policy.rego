package csec603

import rego.v1

default scope_ok := false
scope_ok if input.action in input.delegation.actions

default recipient_ok := true
recipient_ok := false if {
    input.action == "email.send"
    not input.params.to in input.delegation.recipients
}

default vendor_ok := true
vendor_ok := false if {
    input.action == "payments.pay"
    input.params.vendor != "vendor-1"
}

default per_action_ok := true
per_action_ok := false if {
    input.action == "crm.export"
    input.params.limit > 5
}
per_action_ok := false if {
    input.action == "payments.pay"
    input.params.amount > 50
}

default workflow_ok := true
workflow_ok := false if {
    input.condition != "C2-noWF"
    input.action == "crm.export"
    input.workflow.records + input.params.limit > input.delegation.max_records
}
workflow_ok := false if {
    input.condition != "C2-noWF"
    input.action == "payments.pay"
    input.workflow.payment + input.params.amount > input.delegation.max_payment
}

default allow := false
allow if {
    not input.suspended
    scope_ok
    recipient_ok
    vendor_ok
    per_action_ok
    workflow_ok
}

default require_approval := false
require_approval if {
    allow
    input.action in {"files.delete", "email.send", "crm.delete", "payments.pay"}
}

reason := "session_suspended" if input.suspended
else := "scope_denied" if not scope_ok
else := "recipient_denied" if not recipient_ok
else := "vendor_denied" if not vendor_ok
else := "per_action_limit" if not per_action_ok
else := "workflow_limit" if not workflow_ok
else := "allowed"

decision := {"allow": allow, "reason": reason, "require_approval": require_approval}
