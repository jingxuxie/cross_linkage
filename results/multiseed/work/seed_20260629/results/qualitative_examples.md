# Qualitative Example

Synthetic persona: `P0002` (T3).
Document: `P0002_D01`.

This example is synthetic and is intended for defensive privacy evaluation only.

## C0 original

```text
Subject: insurance question
Care team contact record: Ernest Riddle MD; email ernest.riddle.md002@synthetic-example.org; phone (895) 555-9219; mailing address 2906 Melissa Harbors; account ACCT-359340.
This message is for an insurance question. I live around Tacoma and work as a community college lab manager. Because of diabetes medication management and rotating warehouse shifts, I need options that account for single parent of a middle-school student.
```

## C1 direct redaction

```text
Subject: insurance question
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for an insurance question. I live around Tacoma and work as a community college lab manager. Because of diabetes medication management and rotating warehouse shifts, I need options that account for single parent of a middle-school student.
```

## C1b Presidio redaction

```text
Subject: insurance question
Care team contact record: [PRESIDIO_PERSON]; email [PRESIDIO_EMAIL_ADDRESS]; phone [PRESIDIO_PHONE_NUMBER]; mailing address [PRESIDIO_PII]; account [PRESIDIO_PII].
This message is for an insurance question. I live around [PRESIDIO_LOCATION] and work as a community college lab manager. Because of diabetes medication management and rotating warehouse shifts, I need options that account for single parent of a middle-school student.
```

## C4 document-local anonymization proxy

```text
Subject: insurance question
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for an insurance question. I live around a city in the Pacific Northwest and work as a community college lab manager. Because of diabetes medication management and rotating warehouse shifts, I need options that account for single parent of a middle-school student.
```

## C5 LinkGuard

```text
Subject: insurance question
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for an insurance question. I live around a broad location and work as a general worker. Because of health context and availability constraint, I need options that account for family responsibility.
```

## C6 aggressive redaction

```text
Subject: [ISSUE]
Care team contact record: [NAME]; email [EMAIL]; phone [PHONE]; mailing address [ADDRESS]; account [ACCOUNT_ID].
This message is for an [ISSUE]. I live around [LOCATION] and work as a [ROLE]. Because of [MEDICAL_CONTEXT] and [SCHEDULE], I need options that account for [FAMILY_CONTEXT].
```
