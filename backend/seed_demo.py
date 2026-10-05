"""Create a fictional Aman demo organization, web property, and draft policy."""
from __future__ import annotations

import argparse
import json
import secrets
import sys

from aman_api.main import (
    DATABASE_PATH,
    ENVIRONMENT,
    audit,
    canonical_property_origin,
    connection,
    init_db,
    transaction,
    utc_now,
    validate_policy,
)


ORG_NAME = "Banque Démo — données fictives"
PROPERTY_NAME = "Site fictif — développement"
PROPERTY_ORIGIN = "http://localhost:8000"


def demo_policy(property_id: str) -> dict:
    return {
        "schemaVersion": 1,
        "propertyId": property_id,
        "policyVersion": "draft",
        "status": "draft",
        "languages": ["fr", "ar"],
        "defaultLanguage": "fr",
        "retentionDays": 180,
        "purposes": [
            {
                "id": "essential",
                "label": {"fr": "Fonctionnement essentiel", "ar": "الوظائف الأساسية"},
                "description": {
                    "fr": "Fonctions nécessaires dans cet exemple fictif.",
                    "ar": "وظائف ضرورية في هذا المثال الوهمي.",
                },
                "required": True,
                "consentRequired": False,
                "channels": ["web"],
            },
            {
                "id": "analytics",
                "label": {"fr": "Mesure d’audience", "ar": "قياس الجمهور"},
                "description": {
                    "fr": "Mesure fictive, à remplacer par les usages réels du client.",
                    "ar": "قياس وهمي، يُستبدل بالاستخدامات الفعلية للعميل.",
                },
                "required": False,
                "consentRequired": True,
                "channels": ["web"],
            },
            {
                "id": "marketing",
                "label": {"fr": "Personnalisation publicitaire", "ar": "تخصيص الإعلانات"},
                "description": {
                    "fr": "Finalité d’exemple fictive, à faire classifier par le client.",
                    "ar": "غرض تجريبي وهمي، على العميل تصنيفه.",
                },
                "required": False,
                "consentRequired": True,
                "channels": ["web"],
            },
        ],
        "notice": {
            "controllerName": "Entité bancaire fictive de démonstration",
            "contact": "privacy@example.invalid",
            "processingReference": "Référence fictive à remplacer et faire valider",
            "dataCategories": ["Préférences de démonstration uniquement"],
            "recipients": ["Aucun fournisseur réel configuré dans cette démo"],
            "transfers": ["Aucun transfert réel configuré dans cette démo"],
        },
        "noticeTranslations": {
            "fr": {
                "controllerName": "Entité bancaire fictive de démonstration",
                "contact": "privacy@example.invalid",
                "processingReference": "Référence fictive à remplacer et faire valider",
                "dataCategories": ["Préférences de démonstration uniquement"],
                "recipients": ["Aucun fournisseur réel configuré dans cette démo"],
                "transfers": ["Aucun transfert réel configuré dans cette démo"],
            },
            "ar": {
                "controllerName": "كيان مصرفي افتراضي لأغراض العرض التوضيحي",
                "contact": "privacy@example.invalid",
                "processingReference": "مرجع افتراضي يجب استبداله والتحقق منه",
                "dataCategories": ["تفضيلات تجريبية فقط"],
                "recipients": ["لم يتم إعداد أي مزود حقيقي في هذا العرض"],
                "transfers": ["لم يتم إعداد أي تحويل فعلي في هذا العرض"],
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-email", help="Email of the existing Aman user who will own the demo organization")
    args = parser.parse_args()
    if ENVIRONMENT != "development":
        print("Demo seeding is allowed only in the development environment.", file=sys.stderr)
        return 2

    init_db()
    with connection() as conn:
        if args.owner_email:
            users = conn.execute(
                "SELECT id,email FROM users WHERE lower(email)=lower(?) AND disabled=0", (args.owner_email.strip(),)
            ).fetchall()
        else:
            existing_owner = conn.execute(
                "SELECT u.id,u.email FROM users u JOIN memberships m ON m.user_id=u.id "
                "JOIN organizations o ON o.id=m.org_id WHERE o.name=? AND m.role='owner' AND u.disabled=0",
                (ORG_NAME,),
            ).fetchone()
            users = [existing_owner] if existing_owner else conn.execute(
                "SELECT id,email FROM users WHERE disabled=0 ORDER BY created_at"
            ).fetchall()
    if len(users) != 1:
        print("Select exactly one active owner with --owner-email (or create the first admin account).", file=sys.stderr)
        return 2

    owner = users[0]
    now = utc_now()
    with transaction() as conn:
        organization = conn.execute("SELECT id FROM organizations WHERE name=?", (ORG_NAME,)).fetchone()
        if organization:
            org_id = organization["id"]
            if not conn.execute("SELECT 1 FROM memberships WHERE org_id=? AND user_id=?", (org_id, owner["id"])).fetchone():
                print("The fictional demo organization already exists under another account; no changes made.", file=sys.stderr)
                return 2
        else:
            org_id = secrets.token_hex(16)
            conn.execute(
                "INSERT INTO organizations(id,name,require_two_person_publish,created_at) VALUES(?,?,1,?)",
                (org_id, ORG_NAME, now),
            )
            conn.execute(
                "INSERT INTO memberships(org_id,user_id,role,created_at) VALUES(?,?,?,?)",
                (org_id, owner["id"], "owner", now),
            )
            audit(conn, org_id, owner["id"], "organization.created", "organization", org_id,
                  {"source": "local_demo_seed", "fictitious": True})

        prop = conn.execute(
            "SELECT id,environment,origin FROM properties WHERE org_id=? AND name=? AND channel='web'",
            (org_id, PROPERTY_NAME),
        ).fetchone()
        if prop:
            property_id = prop["id"]
            if prop["environment"] != "development" or prop["origin"] != PROPERTY_ORIGIN:
                print("The existing demo property differs from the expected local configuration; no changes made.", file=sys.stderr)
                return 2
        else:
            property_id = secrets.token_urlsafe(24)
            origin = canonical_property_origin(PROPERTY_ORIGIN, allow_loopback_http=True)
            conn.execute(
                "INSERT INTO properties(id,org_id,name,channel,environment,origin,created_at) VALUES(?,?,?,'web','development',?,?)",
                (property_id, org_id, PROPERTY_NAME, origin, now),
            )
            audit(conn, org_id, owner["id"], "property.created", "property", property_id,
                  {"channel": "web", "environment": "development", "origin": origin, "fictitious": True})

        draft = conn.execute(
            "SELECT id,version FROM policies WHERE property_id=? AND status='draft' ORDER BY version DESC LIMIT 1",
            (property_id,),
        ).fetchone()
        if draft:
            policy_id, version = draft["id"], draft["version"]
        else:
            version = conn.execute(
                "SELECT COALESCE(MAX(version),0)+1 AS n FROM policies WHERE property_id=?", (property_id,)
            ).fetchone()["n"]
            policy_id = secrets.token_hex(16)
            policy = validate_policy(demo_policy(property_id), property_id, "web")
            policy["policyVersion"] = str(version)
            conn.execute(
                "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at) "
                "VALUES(?,?,?,1,?,'draft',?,?,?)",
                (policy_id, property_id, version, owner["id"],
                 json.dumps(policy, ensure_ascii=False, separators=(",", ":")), owner["id"], now),
            )
            audit(conn, org_id, owner["id"], "policy.draft_created", "policy", policy_id,
                  {"version": version, "channel": "web", "source": "local_demo_seed", "fictitious": True})

    print(f"Fictional demo organization ready: {ORG_NAME}")
    print(f"Organization ID: {org_id}")
    print(f"Development property ID: {property_id}")
    print(f"Draft policy: v{version} (two-person publication remains enabled)")
    print(f"Demo site: http://localhost:8000/demo-site.html?property={property_id}")
    print("Invite and sign in as a second demo member to publish. No consent events or visitor data were generated.")
    print(f"Database: {DATABASE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
