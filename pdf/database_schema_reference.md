# Comprehensive Database Schema Reference

This document details the complete database schema for the Signet-AWS application, derived from the source code. Use this for data normalization and field mapping.

---

## 1. App: `Invoices`
**Core booking and financial records.**

### `Invoice` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | AutoField | Primary Key | |
| `booking_number` | CharField(50) | `unique=True` | **MANDATORY**. Unique Reference ID. |
| `invoice_number` | CharField(50) | `unique=True`, `null=True` | Generated when status is INVOICED/PAID. |
| `sales_agent` | ForeignKey | `User`, `on_delete=PROTECT` | Internal user who owns the booking. |
| `external_agent` | ForeignKey | `Agent`, `null=True` | External agency referrer. |
| `created_at` | DateTime | `default=now` | |
| `created_time` | TimeField | `default='00:00:00'` | |
| `updated_at` | DateTime | `auto_now=True` | |
| `status` | CharField(20) | Choices: `DRAFT`, `DEPOSIT`, `INVOICED`, `PAID`, `CANCELLED`, `MOVED`, `SPLIT`, `PENALTY` | Default: `DRAFT`. |
| `language` | CharField(2) | Choices: `EN`, `ZH`, `MX` | Default: `ZH` (Mandarin). |
| `tag` | CharField(20) | Choices: `AUDIT_SUBMITTED`, `VERIFIED`, `NEEDS_FIX`, `CLARIFY`, `null=True` | Workflow tag. |
| `group_no` | CharField(50) | `blank=True` | Optional grouping identifier. |
| `has_flight_intinerary`| Boolean | `default=False` | True if flight info is required. |
| `supporting_documents`| M2M | `SupportingDocument` | Linked files. |
| `currency` | ForeignKey | `Currency`, `null=True` | Billing currency. |

### `InvoiceItem` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `invoice` | ForeignKey | `Invoice`, `on_delete=CASCADE` | Parent Booking. |
| `client` | ForeignKey | `Client`, `null=True` | **Likely Mandatory** for per-person charges. |
| `description` | CharField(255) | `blank=True` | Line item text. |
| `quantity` | Integer | `default=1` | |
| `unit_price` | Decimal(10,2) | | Price per unit. |
| `total_price` | Decimal(12,2) | `blank=True` | Auto-calc: `qty * unit`. |
| `tour_booking` | ForeignKey | `TourBooking`, `null=True` | Link to specific tour spot. |
| `flight_ticket` | ForeignKey | `FlightTicket`, `null=True` | Link to flight seat. |
| `addon_service` | ForeignKey | `AddonService`, `null=True` | Link to misc service. |
| `coupon` | ForeignKey | `Coupon`, `null=True` | Link if this is a discount. |

### `InvoicePayment` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `invoice` | ForeignKey | `Invoice`, `on_delete=CASCADE` | Parent Booking. |
| `amount` | Decimal(12,2) | | Payment value. |
| `payment_type` | CharField(20) | Choices: `DEPOSIT`, `BALANCE`, `FULL_AMOUNT` | |
| `payment_method` | ForeignKey | `PaymentMethod`, `null=True` | CC, Cash, etc. |
| `date` | Date | `default=now` | |
| `description` | TextField | `blank=True` | Notes. |

### `Coupon` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `code` | CharField(50) | `unique=True`, `null=True` | e.g. "SUMMER2026". |
| `coupon_type` | CharField(20) | Choices: `COUPON`, `DISCOUNT`, `OTHER` | |
| `amount` | Decimal(10,2) | `null=True` | Fixed value. |
| `expiry_date` | Date | `null=True` | |
| `client` | ForeignKey | `Client`, `null=True` | Owner. |
| `invoice_used` | ForeignKey | `Invoice`, `null=True` | Where it was applied. |
| `status` | CharField(20) | Choices: `ACTIVE`, `USED`, `EXPIRED` | |

### `AddonService` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `title` | CharField(200) | | e.g. "Airport Pickup". |
| `default_price` | Decimal(10,2)| `null=True` | Base price. |

---

## 2. App: `Clients`
**Passenger and Customer Data.**

### `Client` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `first_name` | CharField(100) | | |
| `last_name` | CharField(100) | | |
| `gender` | CharField(1) | Choices: `M`, `F`, `X` | Default: `X`. |
| `preferred_language`| CharField(2) | Choices: `EN`, `ZH`, `MX` | Default: `ZH`. |
| `origin` | ForeignKey | `City`, `null=True` | |
| `ethnicity` | ForeignKey | `Ethnicity`, `null=True` | |
| `email` | EmailField | `blank=True` | |
| `phone` | CharField(20) | `blank=True` | |
| `birth_date` | Date | `null=True` | |
| `travel_group` | ForeignKey | `TravelGroup`, `null=True` | Grouping context. |
| `address` | ForeignKey | `Address`, `null=True` | |

### `TravelDocument` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `client` | ForeignKey | `Client`, `on_delete=CASCADE` | Owner. |
| `doc_type` | CharField(20) | Choices: `PASSPORT`, `VISA`, `PR_CARD`, `OTHER`| |
| `doc_number` | CharField(100)| | |
| `expiry_date` | Date | | **Mandatory**. |
| `issuing_country` | CharField(100)| Default: `Unknown` | |

### `TravelGroup` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `name` | CharField(200) | | Group Name. |
| `notes` | TextField | | |

### `Address` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `street_number` | CharField(20) | | |
| `street_name` | CharField(200)| | |
| `city` | CharField(100)| | |
| `country` | CharField(100)| | |
| `postal_code` | CharField(20) | | |

---

## 3. App: `Tours`
**Tour Products and Inventory.**

### `Product` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `country_code` | CharField(3) | | e.g. `JPN`. |
| `unique_seq` | CharField(2) | | e.g. `H4`. |
| `code` | Property | | `JPN...H4`. |

### `TourInstance` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `tour_code` | CharField(50) | `unique=True` | **MANDATORY**. Full code (e.g. `JPN26A06H4`). |
| `product` | ForeignKey | `Product` | Parent definition. |
| `start_date` | Date | `null=True` | Auto-parsed from code. |
| `end_date` | Date | `null=True` | |
| `language` | CharField(2) | Choices: `C`, `M`, `E`, `O` | Tour Language. |
| `status` | CharField(20) | Choices: `OPEN`, `FULL`, `COMPLETED`, `CANCELLED` | |

### `TourBooking` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `tour_instance` | ForeignKey | `TourInstance` | |
| `booking_id` | CharField(50) | `unique=True` | e.g. `JPN...-S-01`. |
| `booking_type` | CharField(20) | Choices: `SINGLE`, `DOUBLE`, `TWIN`, `UPGRADE`, `INFANT` | |
| `room_type` | CharField(50) | `blank=True` | Import raw string (e.g. "Twin #6"). |
| `price` | Decimal | `null=True` | Specific price. |
| `status` | CharField(20) | Choices: `AVAILABLE`, `BOOKED`, `HELD` | |

---

## 4. App: `Flights`
**Air Travel inventory.**

### `Flight` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `airline` | ForeignKey | `Airline` | |
| `flight_number` | CharField(10) | | e.g. `013`. |
| `departure_airport`| ForeignKey | `Airport` | |
| `arrival_airport` | ForeignKey | `Airport` | |

### `FlightInstance` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `flight` | ForeignKey | `Flight` | |
| `flight_code` | CharField(50) | `unique=True` | e.g. `AC013-2026-04-26`. |
| `departure_date` | Date | `null=True` | |

### `FlightTicket` (Model)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `flight` | ForeignKey | `FlightInstance` | |
| `ticket_code` | CharField(100)| `unique=True` | |
| `client` | ForeignKey | `Client`, `null=True` | Passenger. |
| `pnr` | CharField(20) | `blank=True` | e.g. `GMFVXK`. |
| `seat_number` | CharField(10) | `blank=True` | e.g. `32D`. |
| `cabin_class` | CharField(20) | Choices: `Economy`, `Business`, `First` | |

---

## 5. Other Apps

### `Agent` (App: `Agents`)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `agency` | ForeignKey | `Agency` | |
| `department` | CharField | | |

### `Currency` (App: `Currencies`)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `code` | CharField(3) | `unique=True` | e.g. `USD`. |
| `is_base` | Boolean | | |

### `SupportingDocument` (App: `Documents`)
| Field Name | Type | Options / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `title` | CharField | | |
| `file` | FileField | | |
