"""Domain-level exceptions.

Service-layer code raises these instead of framework-specific exceptions,
so business logic stays independent of FastAPI. API route handlers
translate them into the appropriate HTTP response.
"""


class AuthenticationError(Exception):
    """Employee ID not found, or found but not active.

    A single generic message is used for both cases deliberately, so a
    caller cannot use the login endpoint to enumerate valid Employee IDs.
    """


class MaxChildrenExceededError(Exception):
    """The employee already has the maximum of two children on record."""


class DuplicateChildError(Exception):
    """A child with this exact name and date of birth already exists for
    this employee — most likely a duplicate submission (e.g. the user
    resubmitted after a slow response appeared to hang), not two
    genuinely different children."""


class MissingJoinDateError(Exception):
    """The employee's Joindate is not on file, so eligibility (which
    depends on the employee's joining month) cannot be calculated."""


class ChildNotFoundError(Exception):
    """No active child with the given ChildID belongs to this employee."""


class ClaimNotFoundError(Exception):
    """No claim with the given ClaimID belongs to this employee."""


class NoEligibilityForPeriodError(Exception):
    """No eligibility record exists for this child in the financial year
    the claim's invoice date falls in."""


class FirstYearPayoutPeriodError(Exception):
    """The invoice date falls within the child's first 13 months of life,
    which is paid automatically — no claim is needed, or allowed, for
    that period (user direction 2026-09-22/23)."""


class ClaimNotEditableError(Exception):
    """The claim is not in Draft or SentBack status, so it cannot be
    edited, have attachments added, or be (re-)submitted."""


class DuplicateInvoiceError(Exception):
    """A claim already exists for this employee, child, and invoice number
    (see DECISIONS_LOG.md item 39)."""


class InvalidUploadError(Exception):
    """The uploaded file failed extension or content validation (empty file,
    disallowed type) — distinct from FileTooLargeError so callers can map
    it to the more specific 413 status per ERROR_HANDLING_AND_LOGGING.md."""


class FileTooLargeError(Exception):
    """The uploaded file exceeds the configured maximum size."""


class AttachmentNotFoundError(Exception):
    """No attachment with the given AttachmentID belongs to this claim."""


class NotHRApproverError(Exception):
    """The authenticated employee is not a recognized, active HR approver."""


class ClaimNotReviewableError(Exception):
    """The claim is not in Submitted status, so HR cannot approve,
    reject, or send it back."""


class InvalidApprovedAmountError(Exception):
    """The approved amount is not positive, exceeds the invoice amount, or
    exceeds the child's remaining eligibility balance for that financial
    year (see DECISIONS_LOG.md item 44)."""
