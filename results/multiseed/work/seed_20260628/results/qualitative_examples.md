# Qualitative Example

Synthetic persona: `P0002` (T3).
Document: `P0002_D01`.

This example is synthetic and is intended for defensive privacy evaluation only.

## C0 original

```text
Subject: medication refill
Care team contact record: Tammy Daniels; email tammy.daniels002@synthetic-example.org; phone (322) 555-6526; mailing address 6412 Baker Knolls; account ACCT-285976.
This message is for a medication refill. I live around Ogden and work as a community college lab manager. Because of migraine treatment plan and early-morning bus route, I need options that account for shared custody schedule.
```

## C1 direct redaction

```text
Subject: medication refill
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a medication refill. I live around Ogden and work as a community college lab manager. Because of migraine treatment plan and early-morning bus route, I need options that account for shared custody schedule.
```

## C1b Presidio redaction

```text
Subject: medication refill
Care team contact record: [PRESIDIO_PERSON]; email [PRESIDIO_EMAIL_ADDRESS]; phone [PRESIDIO_PHONE_NUMBER]; mailing address [PRESIDIO_PII]; account [PRESIDIO_ACCOUNT_ID].
This message is for a medication refill. I live around [PRESIDIO_LOCATION] and work as a community college lab manager. Because of migraine treatment plan and [PRESIDIO_DATE_TIME] bus route, I need options that account for shared custody schedule.
```

## C4 document-local anonymization proxy

```text
Subject: medication refill
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a medication refill. I live around a city in the Mountain West and work as a community college lab manager. Because of migraine treatment plan and early-morning bus route, I need options that account for shared custody schedule.
```

## C5 LinkGuard

```text
Subject: medication refill
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a medication refill. I live around a broad location and work as a general worker. Because of health context and availability constraint, I need options that account for family responsibility.
```

## C6 aggressive redaction

```text
Subject: [ISSUE]
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for a [ISSUE]. I live around [LOCATION] and work as a [ROLE]. Because of [MEDICAL_CONTEXT] and [SCHEDULE], I need options that account for [FAMILY_CONTEXT].
```
