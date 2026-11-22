"""In-memory repository and billing client for the POS receipt module."""
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Lock
from uuid import uuid4

from app.domain.receipt import BillingReceiptData, ReceiptRecord

BILLING_TIMEOUT_SECONDS = 10


class BillingServiceError(Exception):
    """Raised when the billing module fails, times out or is unreachable."""


class BillingClient:
    """Simulated client for the billing module (API-INT-08 - Comprobantes).

    Replace `_call_billing_api` with a real HTTP call when the API is available.
    `request_receipt` enforces the timeout regardless of the implementation.
    """

    def __init__(
        self,
        simulate_failure: bool = False,
        simulated_delay_seconds: float = 0.0,
    ) -> None:
        self.simulate_failure = simulate_failure
        self.simulated_delay_seconds = simulated_delay_seconds
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _call_billing_api(self, sale_id: int) -> BillingReceiptData:
        if self.simulated_delay_seconds:
            time.sleep(self.simulated_delay_seconds)
        if self.simulate_failure:
            raise BillingServiceError("Billing service returned an error")
        return BillingReceiptData(
            receipt_number=f"CMP-{sale_id:06d}",
            reference=str(uuid4()),
        )

    def request_receipt(self, sale_id: int, timeout_seconds: float) -> BillingReceiptData:
        future = self._executor.submit(self._call_billing_api, sale_id)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise BillingServiceError("Billing service timed out") from exc
        except BillingServiceError:
            raise
        except Exception as exc:
            raise BillingServiceError("Billing service failed") from exc


class ReceiptRepository:
    def __init__(self) -> None:
        self._receipts: dict[int, ReceiptRecord] = {}
        self._lock = Lock()

    def get_by_sale_id(self, sale_id: int) -> ReceiptRecord | None:
        return self._receipts.get(sale_id)

    def create(self, receipt: ReceiptRecord) -> ReceiptRecord:
        with self._lock:
            self._receipts[receipt.sale_id] = receipt
        return receipt