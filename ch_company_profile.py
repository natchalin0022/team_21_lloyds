"""
Companies House — Company Profile: how to call & read every property in Python
==============================================================================
Endpoint:  GET https://api.company-information.service.gov.uk/company/{company_number}
Auth:      HTTP Basic — your API key as the USERNAME, blank password.
Get a free key at https://developer.company-information.service.gov.uk/

Docs for this resource:
https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/companyprofile?v=latest

Deps:  pip install requests
"""

import os
import requests

API_KEY = os.environ.get("CH_API_KEY", "YOUR_API_KEY_HERE")
BASE = "https://api.company-information.service.gov.uk"


def get_profile(company_number: str) -> dict:
    """Fetch the full company-profile JSON object for one company."""
    r = requests.get(f"{BASE}/company/{company_number}",
                     auth=(API_KEY, ""), timeout=30)   # key as username, blank pw
    r.raise_for_status()
    return r.json()


def read_properties(p: dict) -> dict:
    """Access every documented property. .get() returns None if absent."""

    # ---- top-level scalars ----
    company_name        = p.get("company_name")
    company_number      = p.get("company_number")
    company_status      = p.get("company_status")            # e.g. "active"
    company_status_detail = p.get("company_status_detail")
    type_               = p.get("type")                      # e.g. "ltd", "plc", "llp"
    date_of_creation    = p.get("date_of_creation")          # "YYYY-MM-DD"
    date_of_cessation   = p.get("date_of_cessation")
    jurisdiction        = p.get("jurisdiction")
    sic_codes           = p.get("sic_codes", [])             # list of strings
    etag                = p.get("etag")

    # booleans / flags
    has_charges            = p.get("has_charges")
    has_insolvency_history = p.get("has_insolvency_history")
    has_been_liquidated    = p.get("has_been_liquidated")
    has_super_secure_pscs  = p.get("has_super_secure_pscs")
    can_file               = p.get("can_file")
    is_cic                 = p.get("is_community_interest_company")
    ro_in_dispute          = p.get("registered_office_is_in_dispute")
    ro_undeliverable       = p.get("undeliverable_registered_office_address")
    super_secure_officer_count = p.get("super_secure_managing_officer_count")
    last_full_members_list_date = p.get("last_full_members_list_date")

    # ---- nested object: registered_office_address ----
    roa = p.get("registered_office_address", {})
    ro_line_1   = roa.get("address_line_1")
    ro_line_2   = roa.get("address_line_2")
    ro_locality = roa.get("locality")
    ro_region   = roa.get("region")
    ro_postcode = roa.get("postal_code")
    ro_country  = roa.get("country")
    ro_premises = roa.get("premises")
    ro_po_box   = roa.get("po_box")
    ro_care_of  = roa.get("care_of")
    # (service_address has the same shape)
    service_address = p.get("service_address", {})

    # ---- nested object: accounts ----
    accounts = p.get("accounts", {})
    accounts_overdue = accounts.get("overdue")
    accounts_next_due = accounts.get("next_due")
    accounts_next_made_up_to = accounts.get("next_made_up_to")
    # accounting reference date (the day/month the year ends)
    ard = accounts.get("accounting_reference_date", {})
    ard_day, ard_month = ard.get("day"), ard.get("month")
    # last set of accounts filed
    last_acc = accounts.get("last_accounts", {})
    last_acc_type        = last_acc.get("type")          # size proxy: micro/small/...
    last_acc_made_up_to  = last_acc.get("made_up_to")
    last_acc_period_end  = last_acc.get("period_end_on")
    # next accounts due
    next_acc = accounts.get("next_accounts", {})
    next_acc_due_on      = next_acc.get("due_on")
    next_acc_overdue     = next_acc.get("overdue")
    next_acc_period_end  = next_acc.get("period_end_on")

    # ---- nested object: confirmation_statement ----
    cs = p.get("confirmation_statement", {})
    cs_last_made_up_to = cs.get("last_made_up_to")
    cs_next_due        = cs.get("next_due")
    cs_next_made_up_to = cs.get("next_made_up_to")
    cs_overdue         = cs.get("overdue")

    # ---- array: previous_company_names ----
    for prev in p.get("previous_company_names", []):
        _ = prev.get("name"), prev.get("effective_from"), prev.get("ceased_on")

    # ---- nested object: links (URLs to sub-resources) ----
    links = p.get("links", {})
    link_self    = links.get("self")
    link_charges = links.get("charges")           # -> the /charges endpoint (lenders!)
    link_officers = links.get("officers")
    link_psc     = links.get("persons_with_significant_control")
    link_filing  = links.get("filing_history")

    # ---- other nested objects (present only for some company types) ----
    branch  = p.get("branch_company_details", {})
    foreign = p.get("foreign_company_details", {})
    annual_return = p.get("annual_return", {})     # deprecated, legacy companies only

    # return a flat, feature-ready row
    return {
        "company_number": company_number,
        "company_name": company_name,
        "status": company_status,
        "type": type_,
        "date_of_creation": date_of_creation,
        "jurisdiction": jurisdiction,
        "sic_codes": ";".join(sic_codes),
        "has_charges": has_charges,
        "has_insolvency_history": has_insolvency_history,
        "has_been_liquidated": has_been_liquidated,
        "region": ro_region,
        "postcode": ro_postcode,
        "accounts_type": last_acc_type,
        "accounts_last_made_up_to": last_acc_made_up_to,
        "accounts_next_due": next_acc_due_on,
        "accounts_overdue": next_acc_overdue,
        "confirmation_overdue": cs_overdue,
        "charges_url": link_charges,
    }


if __name__ == "__main__":
    profile = get_profile("00000006")   # example company number (string, keep zeros)
    row = read_properties(profile)
    for k, v in row.items():
        print(f"{k:28} {v}")
