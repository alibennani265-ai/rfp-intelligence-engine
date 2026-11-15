import json
from pathlib import Path
from typing import Any

import httpx

MCP_URL = "https://legal.junior-entreprises.com/mcp"
OUTPUT_MD = Path("data/past_studies/CADRE_LEGAL_CNJE_MCP.md")

BASE_LEGAL_MD = """# Cadre Légal et Réglementaire des Junior-Entreprises (CNJE)

## 1. Objet Social, Valeur Pédagogique & Sous-Traitance
- **Obligation de valeur pédagogique :** Toute étude confiée à une Junior-Entreprise (association Loi 1901) doit prolonger l'enseignement dispensé au sein de l'école (ENSEEIHT). Les tâches sans ingénierie (saisie, support niveau 1, exécution pure) sont interdites.
- **Interdiction absolue de sous-traitance :** Une Junior-Entreprise ne peut sous-traiter tout ou partie d'une étude à un tiers externe ou freelance. Seuls les étudiants membres de l'association peuvent intervenir.

## 2. Prohibition de la Régie et du Prêt de Main-d'Œuvre Illicite (Art. L.8241-1 Code du Travail)
- **Forfait au livrable obligatoire :** La Convention d'Étude porte exclusivement sur des livrables définis, chiffrés en Jours-Étude Homme (JEH).
- **Interdiction de mise à disposition / intégration équipe client :** Toute intégration d'un étudiant dans l'équipe du client, tout pointage sur feuille de temps (jours/demi-journées) sous subordination du client ou obligation de présence permanente sur site constitue un délit de prêt de main-d'œuvre illicite et de marchandage (art. L.8231-1 et L.8241-1 du Code du travail).

## 3. Clauses Bloquantes : Pénalités, Garantie, Responsabilité & PI
- **Pénalités de retard déplafonnées INTERDITES :** Les pénalités de retard doivent impérativement être plafonnées (5 % à 10 % du montant HT maximum) et déclenchées uniquement après mise en demeure. Une clause de pénalité déplafonnée est bloquante.
- **Plafond de responsabilité :** La responsabilité de la JE doit être limitée au montant total HT de l'étude.
- **Garantie et Maintenance :** Interdiction des astreintes 24/7, GTR courtes et maintenances pluriannuelles. Seule une garantie de conformité limitée (30 à 90 jours) est autorisée.
- **Propriété Intellectuelle :** Cession des droits subordonnée au paiement intégral de l'étude.
"""


def mcp_rpc(
    client: httpx.Client,
    method: str,
    params: dict[str, Any] | None = None,
    req_id: int = 1,
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        payload["params"] = params
    resp = client.post(MCP_URL, json=payload, headers=headers, timeout=20.0)
    resp.raise_for_status()
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for line in resp.text.splitlines():
            if line.startswith("data: "):
                return dict(json.loads(line[6:]))
    return dict(resp.json())


def sync_cnje_mcp() -> None:
    sections: list[str] = [BASE_LEGAL_MD]
    try:
        with httpx.Client(follow_redirects=True) as client:
            init_res = mcp_rpc(
                client,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "n7-rag", "version": "1.0"},
                },
                req_id=1,
            )
            print("MCP connecté :", init_res.get("result", {}).get("serverInfo", {}))

            tools_res = mcp_rpc(client, "tools/list", {}, req_id=2)
            tools = tools_res.get("result", {}).get("tools", [])
            print("Outils MCP :", [t.get("name") for t in tools])

            queries = [
                "règlement intérieur CNJE critères audit",
                "régie prêt de main d'oeuvre feuille de temps subordination",
                "pénalités de retard plafond responsabilité civile",
                "propriété intellectuelle garantie maintenance sous-traitance",
                "tarification JEH bulletin de versement URSSAF",
            ]
            req_counter = 10
            for tool in tools:
                t_name = tool.get("name", "")
                props = tool.get("inputSchema", {}).get("properties", {})
                str_keys = [k for k, v in props.items() if v.get("type") == "string"]
                if not str_keys:
                    res = mcp_rpc(
                        client,
                        "tools/call",
                        {"name": t_name, "arguments": {}},
                        req_id=req_counter,
                    )
                    req_counter += 1
                    for c in res.get("result", {}).get("content", []):
                        if c.get("text"):
                            sections.append(f"## MCP {t_name}\n\n{c['text']}")
                else:
                    for q in queries:
                        res = mcp_rpc(
                            client,
                            "tools/call",
                            {"name": t_name, "arguments": {str_keys[0]: q}},
                            req_id=req_counter,
                        )
                        req_counter += 1
                        for c in res.get("result", {}).get("content", []):
                            if c.get("text"):
                                sections.append(f"## MCP {t_name} ({q})\n\n{c['text']}")
    except Exception as exc:  # noqa: BLE001
        print(f"Info MCP : {exc}")

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    print(f"[OK] {OUTPUT_MD} généré ({OUTPUT_MD.stat().st_size} octets).")


if __name__ == "__main__":
    sync_cnje_mcp()
