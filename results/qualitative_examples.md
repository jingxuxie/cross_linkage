# Qualitative Example

Synthetic persona: `P0002` (T3).
Document: `P0002_D01`.

This example is synthetic and is intended for defensive privacy evaluation only.

## C0 original

```text
Subject: medication refill
Care team contact record: Dylan Walker; email dylan.walker002@synthetic-example.org; phone (666) 555-1502; mailing address 4687 Wright Flat; account ACCT-673056.
This message is for a medication refill. I live around Tucson and work as a tenant advocate. Because of diabetes medication management and early-morning bus route, I need options that account for caregiver for an older parent.
```

## C1 direct redaction

```text
Subject: medication refill
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a medication refill. I live around Tucson and work as a tenant advocate. Because of diabetes medication management and early-morning bus route, I need options that account for caregiver for an older parent.
```

## C1b Presidio redaction

```text
Subject: medication refill
Care team contact record: [PRESIDIO_PERSON]; email [PRESIDIO_EMAIL_ADDRESS]; phone [PRESIDIO_PHONE_NUMBER]; mailing address [PRESIDIO_PII]; account [PRESIDIO_PII].
This message is for a medication refill. I live around [PRESIDIO_LOCATION] and work as a tenant advocate. Because of diabetes medication management and [PRESIDIO_DATE_TIME] bus route, I need options that account for caregiver for an older parent.
```

## C4 document-local anonymization proxy

```text
Subject: medication refill
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a medication refill. I live around a city in the Southwest and work as a tenant advocate. Because of diabetes medication management and early-morning bus route, I need options that account for caregiver for an older parent.
```

## C5 LinkGuard

```text
Subject: medication refill
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a medication refill. I live around a broad location and work as a general worker. Because of chronic health condition and availability constraint, I need options that account for family responsibility.
```

## C6 aggressive redaction

```text
Subject: [ISSUE]
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a [ISSUE]. I live around [LOCATION] and work as a [ROLE]. Because of [MEDICAL_CONTEXT] and [SCHEDULE], I need options that account for [FAMILY_CONTEXT].
```
