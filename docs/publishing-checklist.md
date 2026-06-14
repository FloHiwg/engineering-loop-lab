# Publishing Checklist

Before publishing a commit, tag, release, or curated run:

- [ ] Run `make publication-check`.
- [ ] Review fixtures and logs for secrets, credentials, and personal data.
- [ ] Remove absolute paths and machine-specific environment values.
- [ ] Confirm draft article notes and interview files remain ignored.
- [ ] Confirm generated runs are ignored unless deliberately curated.
- [ ] Confirm intentional defects are clearly labeled.
- [ ] Record dependency, runtime, model, and policy versions when applicable.
- [ ] Verify the core walkthrough does not require credentials or paid
      services.
- [ ] Test documented commands from a clean checkout.

The automated scanner catches common patterns; it does not replace manual
review.
