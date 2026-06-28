# Noisy-Style Synthetic Example

Synthetic document: `P0002_D01`.

This example is synthetic and intended only for defensive privacy evaluation.

## N0 noisy original

```text
Subject: healthcare / medication refill / follow-up
Portal metadata: Header copied from the system: Dylan Walker (dylan.walker002@synthetic-example.org, (666) 555-1502), 4687 Wright Flat, ACCT-673056.
Short intake summary with details out of chronological order.
The note asks for help with a medication refill, but the story starts with diabetes medication management.
  - Work is described as a tenant advocate.
- The writer also mentions caregiver for an older parent.
Request type: medication refill.
  - Scheduling is constrained by early-morning bus route.
- Location context appears as Tucson.
They want a response that accounts for the constraints above.
```

## C1 direct redaction

```text
Subject: healthcare / medication refill / follow-up
Portal metadata: Header copied from the system: [NAME] ([EMAIL], [PHONE]), [ADDRESS], [ACCOUNT_ID].
Short intake summary with details out of chronological order.
The note asks for help with a medication refill, but the story starts with diabetes medication management.
  - Work is described as a tenant advocate.
- The writer also mentions caregiver for an older parent.
Request type: medication refill.
  - Scheduling is constrained by early-morning bus route.
- Location context appears as Tucson.
They want a response that accounts for the constraints above.
```

## C1b Presidio redaction

```text
Subject: healthcare / medication refill / follow-up
Portal metadata: Header copied from the system: [PRESIDIO_PERSON] ([PRESIDIO_EMAIL_ADDRESS], [PRESIDIO_PII]), [PRESIDIO_DATE_TIME] [PRESIDIO_PERSON], [PRESIDIO_PII].
Short intake summary with details out of chronological order.
The note asks for help with a medication refill, but the story starts with diabetes medication management.
  - Work is described as a tenant advocate.
- The writer also mentions caregiver for an older parent.
Request type: medication refill.
  - Scheduling is constrained by [PRESIDIO_DATE_TIME] bus route.
- Location context appears as [PRESIDIO_LOCATION].
They want a response that accounts for the constraints above.
```

## C4 doc-local proxy

```text
Subject: healthcare / medication refill / follow-up
Portal metadata: Header copied from the system: [NAME] ([EMAIL], [PHONE]), [ADDRESS], [ACCOUNT_ID].
Short intake summary with details out of chronological order.
The note asks for help with a medication refill, but the story starts with diabetes medication management.
  - Work is described as a tenant advocate.
- The writer also mentions caregiver for an older parent.
Request type: medication refill.
  - Scheduling is constrained by early-morning bus route.
- Location context appears as a city in the Southwest.
They want a response that accounts for the constraints above.
```

## C5 LinkGuard

```text
Subject: healthcare / medication refill / follow-up
Portal metadata: Header copied from the system: [NAME] ([EMAIL], [PHONE]), [ADDRESS], [ACCOUNT_ID].
Short intake summary with details out of chronological order.
The note asks for help with a medication refill, but the story starts with chronic health condition.
  - Work is described as a general worker.
- The writer also mentions family responsibility.
Request type: medication refill.
  - Scheduling is constrained by availability constraint.
- Location context appears as a broad location.
They want a response that accounts for the constraints above.
```

## C6 aggressive redaction

```text
Subject: healthcare / [ISSUE] / follow-up
Portal metadata: Header copied from the system: [NAME] ([EMAIL], [PHONE]), [ADDRESS], [ACCOUNT_ID].
Short intake summary with details out of chronological order.
The note asks for help with a [ISSUE], but the story starts with [MEDICAL_CONTEXT].
  - Work is described as a [ROLE].
- The writer also mentions [FAMILY_CONTEXT].
Request type: [ISSUE].
  - Scheduling is constrained by [SCHEDULE].
- Location context appears as [LOCATION].
They want a response that accounts for the constraints above.
```
