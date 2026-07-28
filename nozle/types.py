from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

JSONMapping = Dict[str, Any]


class TrackOptions(TypedDict, total=False):
    subscription_id: str
    transaction_id: str
    timestamp: str


class _CanResultRequired(TypedDict):
    allowed: bool
    used: int
    cost_per_use_cents: int
    revenue_per_use_cents: int
    margin_per_use_cents: int


class CanResult(_CanResultRequired, total=False):
    reason: str
    limit: int
    remaining: int
    overage: bool
    margin_percent: float
    min_margin_percent: float
    margin_level: str
    margin_enforcement_mode: str
    warning: str


class Plan(TypedDict):
    code: str
    name: str
    amount_cents: int
    amount_currency: str
    interval: str


class _StripeCheckoutRequired(TypedDict):
    type: Literal["stripe"]


class StripeCheckoutResult(_StripeCheckoutRequired, total=False):
    client_secret: str
    clientSecret: str
    url: str
    invoice_id: str
    amount_cents: int
    currency: str


class _CompletedCheckoutRequired(TypedDict):
    type: Literal["completed"]
    status: str


class CompletedCheckoutResult(_CompletedCheckoutRequired, total=False):
    subscription_id: str
    plan_code: str


class _ScheduledCheckoutRequired(TypedDict):
    type: Literal["scheduled"]
    status: str


class ScheduledCheckoutResult(_ScheduledCheckoutRequired, total=False):
    subscription_id: str
    plan_code: str


CheckoutResult = Union[StripeCheckoutResult, CompletedCheckoutResult, ScheduledCheckoutResult]


class SubscribeResult(TypedDict):
    subscription_id: str
    status: str


CancellationPolicy = Literal["end_of_period", "immediate"]


class _SubscriptionCancellationRequired(TypedDict):
    external_id: str
    status: str


class SubscriptionCancellation(_SubscriptionCancellationRequired, total=False):
    ending_at: Optional[str]
    terminated_at: Optional[str]


class CancelSubscriptionResult(TypedDict):
    subscription: SubscriptionCancellation


class _PingResultRequired(TypedDict):
    ok: bool
    engine: str


class PingResult(_PingResultRequired, total=False):
    version: str


class _CustomerUpsertResultRequired(TypedDict):
    external_id: str


class CustomerUpsertResult(_CustomerUpsertResultRequired, total=False):
    name: str
    email: str


class CheckAndDeductResult(TypedDict):
    allowed: bool
    remaining: Union[int, float]


class CreditSystem(TypedDict):
    id: str
    code: str
    name: str
    description: Optional[str]
    unit_name: str
    status: str
    created_at: str
    updated_at: str


CreditBalanceSourceType = Literal[
    "subscription_grant",
    "top_up",
    "manual_grant",
    "adjustment",
    "allocated_top_up",
]


class CreditBalanceSource(TypedDict):
    id: str
    entity_id: Optional[str]
    parent_source_id: Optional[str]
    scope: Literal["customer", "entity"]
    transferable: bool
    returnable: bool
    type: CreditBalanceSourceType
    reference: str
    subscription_id: Optional[str]
    initial: str
    remaining: str
    valid_from: str
    expires_at: Optional[str]
    priority: int
    status: str
    available: bool


class CreditBalance(TypedDict):
    customer_id: str
    credit_system: str
    credit_system_id: str
    credit_system_name: str
    unit_name: str
    system_status: str
    available: str
    as_of: str
    sources: List[CreditBalanceSource]


class CreditBalances(TypedDict):
    customer_id: str
    as_of: str
    balances: List[CreditBalance]


class CreditOperationAllocation(TypedDict):
    source_id: str
    source_entity_id: Optional[str]
    source_type: str
    delta: str
    before: str
    after: str


CreditOperationType = Literal[
    "consume", "grant", "adjustment", "expire", "revoke", "refund", "transfer"
]
CreditOperationStatus = Literal["succeeded", "denied", "reversed"]


class CreditOperation(TypedDict):
    id: str
    entity_id: Optional[str]
    credit_system: str
    credit_system_id: str
    credit_system_name: str
    unit_name: str
    billable_metric_code: Optional[str]
    type: CreditOperationType
    status: CreditOperationStatus
    metric_amount: Optional[str]
    credit_amount: str
    rate_id: Optional[str]
    rate_metric_amount: Optional[str]
    rate_credit_amount: Optional[str]
    reason: Optional[str]
    occurred_at: str
    source_allocations: List[CreditOperationAllocation]


class CreditOperationPage(TypedDict):
    customer_id: str
    operations: List[CreditOperation]
    next_cursor: Optional[str]


CustomerEntityStatus = Literal["active", "suspended", "deleted"]


class CustomerEntity(TypedDict):
    id: str
    customer_id: str
    external_id: str
    name: Optional[str]
    status: CustomerEntityStatus
    metadata: JSONMapping
    created_at: str
    updated_at: str
    deleted_at: Optional[str]


class _CustomerEntityUpsertRequired(TypedDict):
    status: CustomerEntityStatus


class CustomerEntityUpsertData(_CustomerEntityUpsertRequired, total=False):
    name: Optional[str]
    metadata: JSONMapping


class CustomerEntityBulkUpsertItem(CustomerEntityUpsertData):
    external_id: str


CustomerEntityAction = Literal[
    "created", "updated", "unchanged", "activated", "reactivated", "suspended", "deleted"
]


class CustomerEntityMutationResult(TypedDict):
    action: CustomerEntityAction
    entity: CustomerEntity
    replayed: bool


class CustomerEntityPage(TypedDict):
    customer_id: str
    entities: List[CustomerEntity]
    next_cursor: Optional[str]


class CustomerEntityBulkMutationCounts(TypedDict):
    created: int
    updated: int
    unchanged: int
    activated: int
    reactivated: int
    suspended: int
    deleted: int


class CustomerEntityBulkMutationItem(TypedDict):
    action: CustomerEntityAction
    entity: CustomerEntity


class CustomerEntityBulkMutationResult(TypedDict):
    customer_id: str
    entities: List[CustomerEntityBulkMutationItem]
    counts: CustomerEntityBulkMutationCounts
    replayed: bool


EntityCreditPoolPolicy = Literal["entity_only", "entity_then_customer", "customer_only"]


class EntityCreditBalance(TypedDict):
    customer_id: str
    entity_id: str
    entity_status: CustomerEntityStatus
    credit_system: str
    credit_system_id: str
    credit_system_name: str
    unit_name: str
    system_status: str
    entity_available: str
    shared_available: str
    effective_available: str
    consumed: str
    pool_policy: Optional[EntityCreditPoolPolicy]
    as_of: str
    sources: List[CreditBalanceSource]


class EntityCreditBalances(TypedDict):
    customer_id: str
    entity_id: str
    entity_status: CustomerEntityStatus
    as_of: str
    balances: List[EntityCreditBalance]


class EntityCreditOperationPage(CreditOperationPage):
    entity_id: str


class _EntityCreditTransferSourceRequired(TypedDict):
    source_id: str
    source_type: Literal["top_up", "allocated_top_up"]
    scope: Literal["customer", "entity"]
    amount: str
    before: str
    after: str
    expires_at: Optional[str]


class EntityCreditTransferSource(_EntityCreditTransferSourceRequired, total=False):
    parent_source_id: Optional[str]
    created: bool


class _EntityCreditTransferResultRequired(TypedDict):
    transferred: bool
    operation_id: str
    customer_id: str
    entity_id: str
    credit_system: str
    direction: Literal["allocation", "deallocation"]
    amount: str
    available: str
    parent_sources: List[EntityCreditTransferSource]
    entity_sources: List[EntityCreditTransferSource]
    replayed: bool


class EntityCreditTransferResult(_EntityCreditTransferResultRequired, total=False):
    reason: str


class _UsageDeductionRequired(TypedDict):
    source_type: str
    source_scope: str
    amount: str
    remaining: str


class UsageDeduction(_UsageDeductionRequired, total=False):
    balance_source_id: str


class _UsageCheckResultRequired(TypedDict):
    advisory: Literal[True]
    allowed: bool
    metric_amount: str
    credit_system: str
    credits_required: str
    available: str


class UsageCheckResult(_UsageCheckResultRequired, total=False):
    entity_id: str
    pool_policy: str
    projected_remaining: str
    projected_deductions: List[UsageDeduction]
    reason: str


class _UsageTrackResultRequired(TypedDict):
    allowed: bool


class UsageTrackResult(_UsageTrackResultRequired, total=False):
    operation_id: str
    entity_id: str
    pool_policy: str
    metric_amount: str
    credit_system: str
    credits_required: str
    credits_consumed: str
    available: str
    remaining: str
    reason: str
    deductions: List[UsageDeduction]
