
from locust import HttpUser, task, between
from datetime import date, timedelta
from threading import Lock
from typing import Any
import logging
import os
import random

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# /locust is mounted read-only in Docker.
# /tmp is writable inside the Locust container.
LOG_DIR = "/tmp/locust/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f"{LOG_DIR}/locust_test.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"

# Shared by users within a Locust process.
# Each Locust worker process has its own copy.
_setup_lock = Lock()
_setup_complete = False
_shared_guest_ids: list[int] = []
_shared_unit_ids: list[int] = []


def response_id(response) -> int | None:
    """Extract an integer ID from a successful API response."""
    try:
        data = response.json()
        value = data.get("id") if isinstance(data, dict) else None
        return int(value) if value is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


class ReservationUser(HttpUser):
    host = "http://app:8000"
    wait_time = between(1, 3)

    def on_start(self):
        """Prepare shared test data once per Locust worker process."""
        global _setup_complete

        self.reservation_ids: list[int] = []

        with _setup_lock:
            if not _setup_complete:
                self._initialize_shared_data()
                _setup_complete = True

        # Each simulated user uses the data created by setup.
        self.guest_ids = list(_shared_guest_ids)
        self.unit_ids = list(_shared_unit_ids)

        if not self.guest_ids or not self.unit_ids:
            logger.warning(
                "No usable guests or units. "
                "Check the API payloads and endpoint responses."
            )

    def _initialize_shared_data(self):
        """
        Create a small pool of guests and units per Locust worker.

        For a repeatable test, use a separate seed-data step instead.
        """
        logger.info("Initializing Locust test data")

        # Create a small number of units.
        for i in range(1, 6):
            payload = {
                "name": f"Locust Unit {i}",
                "description": f"Load-test unit {i}",
                "capacity": random.randint(2, 6),
                "price_per_night": round(random.uniform(100, 500), 2),
            }

            try:
                with self.client.post(
                    f"{API_PREFIX}/units/",
                    json=payload,
                    name="Setup: create unit",
                    catch_response=True,
                ) as response:
                    if response.status_code not in (200, 201):
                        response.failure(
                            f"Unit creation failed: "
                            f"{response.status_code} {response.text}"
                        )
                        continue

                    unit_id = response_id(response)
                    if unit_id is None:
                        response.failure(
                            "Unit response did not contain an integer 'id'"
                        )
                        continue

                    _shared_unit_ids.append(unit_id)
                    logger.info("Created test unit id=%s", unit_id)

            except Exception:
                logger.exception("Error while creating test unit")

        # Create a small number of guests.
        for i in range(1, 11):
            payload = {
                "name": f"Locust Guest {i}",
                "email": f"locust_guest_{i}@example.com",
                "phone": f"700000{i:04d}",
            }

            try:
                with self.client.post(
                    f"{API_PREFIX}/guests/",
                    json=payload,
                    name="Setup: create guest",
                    catch_response=True,
                ) as response:
                    if response.status_code not in (200, 201):
                        response.failure(
                            f"Guest creation failed: "
                            f"{response.status_code} {response.text}"
                        )
                        continue

                    guest_id = response_id(response)
                    if guest_id is None:
                        response.failure(
                            "Guest response did not contain an integer 'id'"
                        )
                        continue

                    _shared_guest_ids.append(guest_id)
                    logger.info("Created test guest id=%s", guest_id)

            except Exception:
                logger.exception("Error while creating test guest")

        logger.info(
            "Test data initialized: %s units, %s guests",
            len(_shared_unit_ids),
            len(_shared_guest_ids),
        )

    @task(3)
    def list_guests(self):
        """Exercise the guest-list endpoint."""
        self.client.get(
            f"{API_PREFIX}/guests/",
            name="GET guests",
        )

    @task(3)
    def list_units(self):
        """Exercise the unit-list endpoint."""
        self.client.get(
            f"{API_PREFIX}/units/",
            name="GET units",
        )

    @task(2)
    def create_reservation(self):
        """Create one reservation per task invocation."""
        if not self.guest_ids or not self.unit_ids:
            return

        guest_id = random.choice(self.guest_ids)
        unit_id = random.choice(self.unit_ids)

        # Vary the future date range to reduce booking conflicts.
        check_in_date = date.today() + timedelta(
            days=random.randint(10, 180)
        )
        check_out_date = check_in_date + timedelta(
            days=random.randint(1, 5)
        )

        payload = {
            "guest_id": guest_id,
            "unit_id": unit_id,
            "check_in_date": check_in_date.isoformat(),
            "check_out_date": check_out_date.isoformat(),
            "adults": random.randint(1, 4),
            "children": random.randint(0, 3),
        }

        with self.client.post(
            f"{API_PREFIX}/reservations/",
            json=payload,
            name="POST reservation",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(
                    f"Reservation failed: "
                    f"{response.status_code} {response.text}"
                )
                return

            reservation_id = response_id(response)
            if reservation_id is None:
                response.failure(
                    "Reservation response did not contain an integer 'id'"
                )
                return

            self.reservation_ids.append(reservation_id)

            # Keep memory use bounded during long load tests.
            if len(self.reservation_ids) > 100:
                self.reservation_ids.pop(0)

            logger.info(
                "Created reservation id=%s unit_id=%s guest_id=%s",
                reservation_id,
                unit_id,
                guest_id,
            )

    @task(2)
    def get_reservation(self):
        """Retrieve a reservation created by this simulated user."""
        if not self.reservation_ids:
            return

        reservation_id = random.choice(self.reservation_ids)

        self.client.get(
            f"{API_PREFIX}/reservations/{reservation_id}",
            name="GET reservation by ID",
        )


__all__ = ["ReservationUser"]
