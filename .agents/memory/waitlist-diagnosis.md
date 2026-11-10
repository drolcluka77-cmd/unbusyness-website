---
name: Waitlist diagnosis
description: Evidence required before attributing a failed signup to email or database delivery.
---

Do not infer an SMTP or database outage from a generic form error. Establish the actual response status and whether the relevant submission was stored before naming a cause.

**Why:** A reported home-form failure could not be reproduced in a real development browser, while production database checks were healthy. The old form text grouped validation, throttling, network, and storage failures under the same sending error.

**How to apply:** Compare the exact affected page's payload with server validation and distinguish development tests from production evidence. Avoid claiming that a diagnostic improvement resolves an unconfirmed original failure.
