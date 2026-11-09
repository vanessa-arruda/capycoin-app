from enum import StrEnum


class UserRole(StrEnum):
    PARENT = "parent"
    KID = "kid"


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class Recurrence(StrEnum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class CreditTransactionKind(StrEnum):
    TASK_REWARD = "task_reward"
    PRIZE_CLAIM = "prize_claim"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class NotificationType(StrEnum):
    TASK_SUBMITTED = "task_submitted"
    TASK_APPROVED = "task_approved"
    TASK_DENIED = "task_denied"
    PRIZE_CLAIMED = "prize_claimed"
    PRIZE_CLAIM_APPROVED = "prize_claim_approved"
    PRIZE_CLAIM_DENIED = "prize_claim_denied"
    CREDITS_ADJUSTED = "credits_adjusted"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
