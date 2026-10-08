"""Create a fictional Aman demo organization, web and mobile properties, and draft policies."""
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
DEMO_PROPERTIES = (
    {"name": "Site fictif — développement", "channel": "web", "origin": "http://localhost:8000", "retention_days": 180},
    {"name": "Application iOS fictive — développement", "channel": "ios", "origin": None, "retention_days": 30},
    {"name": "Application Android fictive — développement", "channel": "android", "origin": None, "retention_days": 30},
)


def demo_policy(property_id: str, channel: str, retention_days: int) -> dict:
    if channel == "web":
        optional_purposes = [
            (
                "analytics",
                "Mesure d’audience",
                "قياس الجمهور",
                "Mesure fictive, à remplacer par les usages réels du client.",
                "قياس وهمي، يُستبدل بالاستخدامات الفعلية للعميل.",
            ),
            (
                "marketing",
                "Personnalisation publicitaire",
                "تخصيص الإعلانات",
                "Finalité d’exemple fictive, à faire classifier par le client.",
                "غرض تجريبي وهمي، على العميل تصنيفه.",
            ),
        ]
    else:
        optional_purposes = [
            (
                "analytics",
                "Mesure d’usage de démonstration",
                "قياس الاستخدام لأغراض العرض",
                "Mesure fictive de l’application, à remplacer et faire classifier par le client.",
                "قياس افتراضي للتطبيق، يجب استبداله وتصنيفه من قبل العميل.",
            ),
            (
                "personalization",
                "Personnalisation de démonstration",
                "التخصيص لأغراض العرض",
                "Personnalisation fictive de l’interface, à remplacer et faire classifier par le client.",
                "تخصيص افتراضي للواجهة، يجب استبداله وتصنيفه من قبل العميل.",
            ),
        ]

    purposes = [{
        "id": "essential",
        "label": {"fr": "Fonctionnement essentiel", "ar": "الوظائف الأساسية"},
        "description": {
            "fr": "Fonctions nécessaires dans cet exemple fictif ; classification à valider.",
            "ar": "وظائف ضرورية في هذا المثال الوهمي؛ يجب التحقق من تصنيفها.",
        },
        "required": True,
        "consentRequired": False,
        "initiallyEnabled": True,
        "channels": [channel],
    }]
    purposes.extend({
        "id": purpose_id,
        "label": {"fr": french_label, "ar": arabic_label},
        "description": {"fr": french_description, "ar": arabic_description},
        "required": False,
        "consentRequired": True,
        "initiallyEnabled": False,
        "channels": [channel],
    } for purpose_id, french_label, arabic_label, french_description, arabic_description in optional_purposes)
    return {
        "schemaVersion": 1,
        "propertyId": property_id,
        "policyVersion": "draft",
        "status": "draft",
        "languages": ["fr", "ar"],
        "defaultLanguage": "fr",
        "retentionDays": retention_days,
        "purposes": purposes,
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

        existing_properties = {}
        for definition in DEMO_PROPERTIES:
            property_name = definition["name"]
            channel = definition["channel"]
            prop = conn.execute(
                "SELECT id,environment,origin FROM properties WHERE org_id=? AND name=? AND channel=?",
                (org_id, property_name, channel),
            ).fetchone()
            if prop:
                expected_origin = (canonical_property_origin(definition["origin"], allow_loopback_http=True)
                                   if definition["origin"] else None)
                if prop["environment"] != "development" or prop["origin"] != expected_origin:
                    print(f"The existing demo property '{property_name}' differs from the expected local configuration; no changes made.", file=sys.stderr)
                    return 2
            existing_properties[(channel, property_name)] = prop

        seeded_properties = []
        for definition in DEMO_PROPERTIES:
            property_name = definition["name"]
            channel = definition["channel"]
            configured_origin = definition["origin"]
            prop = existing_properties[(channel, property_name)]
            if prop:
                property_id = prop["id"]
            else:
                property_id = secrets.token_urlsafe(24)
                origin = (canonical_property_origin(configured_origin, allow_loopback_http=True)
                          if configured_origin else None)
                conn.execute(
                    "INSERT INTO properties(id,org_id,name,channel,environment,origin,created_at) VALUES(?,?,?,?,?,?,?)",
                    (property_id, org_id, property_name, channel, "development", origin, now),
                )
                audit(conn, org_id, owner["id"], "property.created", "property", property_id,
                      {"channel": channel, "environment": "development", "origin": origin, "fictitious": True})

            draft = conn.execute(
                "SELECT id,version FROM policies WHERE property_id=? AND status='draft' ORDER BY version DESC LIMIT 1",
                (property_id,),
            ).fetchone()
            if draft:
                version = draft["version"]
            else:
                version = conn.execute(
                    "SELECT COALESCE(MAX(version),0)+1 AS n FROM policies WHERE property_id=?", (property_id,)
                ).fetchone()["n"]
                policy_id = secrets.token_hex(16)
                policy = validate_policy(
                    demo_policy(property_id, channel, definition["retention_days"]), property_id, channel
                )
                policy["policyVersion"] = str(version)
                conn.execute(
                    "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at) "
                    "VALUES(?,?,?,1,?,'draft',?,?,?)",
                    (policy_id, property_id, version, owner["id"],
                     json.dumps(policy, ensure_ascii=False, separators=(",", ":")), owner["id"], now),
                )
                audit(conn, org_id, owner["id"], "policy.draft_created", "policy", policy_id,
                      {"version": version, "channel": channel, "source": "local_demo_seed", "fictitious": True})
            seeded_properties.append({"name": property_name, "channel": channel, "id": property_id,
                                     "version": version, "retention_days": definition["retention_days"]})

    print(f"Fictional demo organization ready: {ORG_NAME}")
    print(f"Organization ID: {org_id}")
    for seeded_property in seeded_properties:
        print(f"{seeded_property['channel']} property ID: {seeded_property['id']}")
        print(f"  {seeded_property['name']} · draft v{seeded_property['version']} · {seeded_property['retention_days']} illustrative days")
    web_property = next(item for item in seeded_properties if item["channel"] == "web")
    print(f"Demo site: http://localhost:8000/demo-site.html?property={web_property['id']}")
    print("Invite and sign in as a second demo member to publish. No consent events or visitor data were generated.")
    print(f"Database: {DATABASE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
