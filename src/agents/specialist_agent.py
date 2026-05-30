"""Generic Specialist Agent Implementation.

A single parameterized class for all 16 specialist agents.
Each agent is differentiated by its ``SpecialistDefinition`` and
domain description — the logic (compound BM25, relevance-check,
structured JSON analysis) is shared via ``BaseSpecialistAgent``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base_agent import BaseSpecialistAgent
from src.agents.schemas import ActiveSpecialistManifest, AgentName, SpecialistDefinition

if TYPE_CHECKING:
    from src.llm.client import LLMClientProtocol
    from src.search.search_engine import SparseSearchEngine

# ---------------------------------------------------------------------------
# Domain descriptions for each of the 16 specialists
# ---------------------------------------------------------------------------

DOMAIN_DESCRIPTIONS: dict[AgentName, str] = {
    AgentName.IP: (
        "intellectual property rights, patents, trademarks, copyrights, "
        "trade secrets, and license assignments"
    ),
    AgentName.LITIGATION: (
        "pending or threatened litigation, lawsuits, disputes, "
        "arbitration proceedings, and settlements"
    ),
    AgentName.REGULATORY: (
        "regulatory compliance, permits, antitrust, merger control, "
        "government approvals, and change-of-control triggers"
    ),
    AgentName.PRIVACY: (
        "data protection, privacy obligations, GDPR, CCPA, "
        "personal data processing, and breach notification requirements"
    ),
    AgentName.FINANCE: (
        "financial statements, P&L, cash flow, balance sheets, "
        "debt covenants, liens, foreign exchange hedging, and liability caps"
    ),
    AgentName.TAX: (
        "tax provisions, tax returns, withholding obligations, "
        "VAT, sales tax, and tax audit exposure"
    ),
    AgentName.INSURANCE: (
        "insurance policies, coverage gaps, premium obligations, "
        "insurer commitments, and underwriting requirements"
    ),
    AgentName.HR: (
        "employment terms, staff and benefits, compensation, severance, "
        "non-compete clauses, and workforce obligations"
    ),
    AgentName.GOVERNANCE: (
        "corporate governance, bylaws, board composition, shareholder "
        "agreements, cap table structures, and equity arrangements"
    ),
    AgentName.RELATED_PARTY: (
        "related party transactions, affiliate dealings, insider deals, "
        "beneficial ownership, and conflicts of interest"
    ),
    AgentName.CYBER: (
        "cybersecurity posture, IT security controls, hosting "
        "infrastructure, source code management, and software dependencies"
    ),
    AgentName.ASSETS: (
        "tangible and intangible assets, property, equipment, "
        "leases, title encumbrances, and asset transfer conditions"
    ),
    AgentName.SUPPLIER: (
        "supplier relationships, vendor contracts, supply chain risks, "
        "procurement dependencies, and distributor agreements"
    ),
    AgentName.CUSTOMER: (
        "customer contracts, revenue concentration, key account "
        "dependencies, renewal terms, churn exposure, and receivables"
    ),
    AgentName.REPUTATION: (
        "reputational risks, adverse media exposure, brand protection, "
        "corruption allegations, and whistleblower incidents"
    ),
    AgentName.ESG: (
        "environmental compliance, emissions, hazardous waste management, "
        "sustainability obligations, and ESG reporting requirements"
    ),
}


DOMAIN_INSTRUCTIONS: dict[AgentName, str] = {
    AgentName.IP: (
        "- Missing or incomplete IP ownership transfers — look for carve-outs, retained licences, or shared ownership.\n"
        "- Open-source licence contamination that may restrict commercial use (GPL, AGPL).\n"
        "- In-licences that do not survive change of control or cannot be assigned without consent.\n"
        "- Pending or threatened patent infringement claims.\n"
        "- Invention assignment gaps: employees or contractors who have not signed IP assignment agreements.\n"
        "- Trade secret protection weaknesses (no NDA, no clean-room process)."
    ),
    AgentName.LITIGATION: (
        "- Pending or threatened lawsuits with potential damages above $500k.\n"
        "- Contingent liabilities not adequately reserved on the balance sheet.\n"
        "- Statute of limitations exposure for undisclosed historical claims.\n"
        "- Regulatory investigations, enforcement actions, or government subpoenas.\n"
        "- Settlement terms that survive the transaction or restrict future business.\n"
        "- Indemnification obligations from prior M&A transactions still open."
    ),
    AgentName.REGULATORY: (
        "- Antitrust / merger control filings required in any jurisdiction (HSR, EU Phase II, CMA).\n"
        "- Permits, licences, or government authorisations that do not transfer automatically.\n"
        "- Change-of-control provisions in government contracts or regulated licences.\n"
        "- Sanctions exposure — dealings with OFAC-listed entities or restricted countries.\n"
        "- Industry-specific regulatory approvals (banking, healthcare, defence) with long lead times.\n"
        "- Material compliance failures or consent orders with regulators."
    ),
    AgentName.PRIVACY: (
        "- Unlawful cross-border data transfers (SCCs absent or invalid post-Schrems II).\n"
        "- Processing personal data without a valid legal basis under GDPR / CCPA.\n"
        "- Data breach history — unreported incidents or ongoing regulatory investigations.\n"
        "- Third-party data sharing agreements that restrict use or require consent.\n"
        "- Data retention policies that conflict with applicable law.\n"
        "- Consent mechanisms that are pre-ticked, bundled, or otherwise invalid."
    ),
    AgentName.FINANCE: (
        "- Debt covenant violations or headroom below 10% of threshold.\n"
        "- Off-balance-sheet liabilities (operating leases pre-IFRS 16, SPVs, guarantees).\n"
        "- Undisclosed liens or security interests against material assets.\n"
        "- Aggressive revenue recognition — channel stuffing, bill-and-hold, incomplete deliveries.\n"
        "- Working capital normalisation adjustments that inflate EBITDA.\n"
        "- FX exposure without adequate hedging, or hedges that expire at closing.\n"
        "- Material related-party loans or intercompany balances that must unwind."
    ),
    AgentName.TAX: (
        "- Open tax years or ongoing audits with potential assessments.\n"
        "- Transfer pricing arrangements that are not arm's length or lack documentation.\n"
        "- Deferred tax assets dependent on future profitability that may not materialise.\n"
        "- Withholding tax obligations on dividends, royalties, or intercompany payments.\n"
        "- VAT / GST non-compliance or historic under-declaration.\n"
        "- Change-of-control triggering tax recapture, loss disallowance, or accelerated payments.\n"
        "- Thin capitalisation or interest deductibility limitations under BEPS."
    ),
    AgentName.INSURANCE: (
        "- Coverage gaps against key operational risks (cyber, D&O, product liability, E&O).\n"
        "- Policies that lapse or require re-underwriting on change of control.\n"
        "- Claims history indicating systemic risk or potential future losses.\n"
        "- Self-insured retentions or deductibles that materially exceed budget.\n"
        "- Occurrence vs claims-made policy distinctions leaving pre-closing losses uninsured.\n"
        "- Underwriting exclusions for known risks (e.g. PFAS, asbestos, pandemic)."
    ),
    AgentName.HR: (
        "- Retention risk for key personnel — absence of post-closing lock-up or non-solicitation terms.\n"
        "- Change-of-control bonuses or acceleration clauses that increase closing costs.\n"
        "- Underfunded defined benefit pension obligations.\n"
        "- Misclassification of employees as independent contractors (wage, tax, benefits exposure).\n"
        "- Outstanding wage-and-hour claims or unpaid overtime liabilities.\n"
        "- Non-compete or non-solicitation agreements that are unenforceable in the target's jurisdiction.\n"
        "- TUPE / WARN Act obligations on workforce restructuring post-closing."
    ),
    AgentName.GOVERNANCE: (
        "- Anti-takeover provisions (poison pill, staggered board, supermajority voting) that complicate the deal.\n"
        "- Shareholder approval thresholds not met by the current deal structure.\n"
        "- Founder or management share classes with disproportionate voting rights.\n"
        "- Cap table errors — missing option grants, unvested shares not lapsing, phantom equity plans.\n"
        "- Side letters or special rights granted to investors not disclosed in standard documents.\n"
        "- Board composition obligations in shareholder agreements that survive post-closing."
    ),
    AgentName.RELATED_PARTY: (
        "- Transactions with founders, directors, or major shareholders not at arm's length.\n"
        "- Family-member employment or service agreements at above-market rates.\n"
        "- IP or real estate owned by an insider and licensed to the target on non-market terms.\n"
        "- Loans to directors or officers that violate corporate law or must be repaid at closing.\n"
        "- Conflicts of interest not disclosed to the board or not approved by independent directors.\n"
        "- Beneficial ownership obscured through nominee structures or trusts."
    ),
    AgentName.CYBER: (
        "- Known unpatched critical vulnerabilities (CVSS ≥ 9.0) in production systems.\n"
        "- Absence of SOC 2 Type II, ISO 27001, or equivalent certification for a SaaS business.\n"
        "- Third-party source code with restrictive licences embedded in proprietary products.\n"
        "- Customer data stored without encryption at rest or in transit.\n"
        "- Incident response plan absent or untested in the last 12 months.\n"
        "- Shadow IT — business-critical processes running on unsanctioned tools.\n"
        "- Pending cyber insurance claim or prior breach affecting customer data."
    ),
    AgentName.ASSETS: (
        "- Title defects or encumbrances on real property being acquired.\n"
        "- Lease assignment restrictions or landlord consent requirements on key premises.\n"
        "- Equipment subject to finance leases or hire-purchase agreements not disclosed in liabilities.\n"
        "- Environmental contamination or hazardous materials on owned or leased sites.\n"
        "- Assets pledged as collateral that must be released at closing.\n"
        "- Depreciation policies that accelerate asset life, inflating near-term EBITDA."
    ),
    AgentName.SUPPLIER: (
        "- Single-source suppliers for materials or services critical to revenue.\n"
        "- Supplier contracts that terminate or require renegotiation on change of control.\n"
        "- Volume-based pricing tiers that reset post-acquisition, increasing COGS.\n"
        "- Supply chain concentration in sanctioned jurisdictions or geopolitically risky regions.\n"
        "- Outstanding supplier disputes or pending force majeure claims.\n"
        "- Long-term fixed-price supply agreements that become loss-making in inflationary environments."
    ),
    AgentName.CUSTOMER: (
        "- Revenue concentration — top 3 customers representing more than 30% of total revenue.\n"
        "- Customer contracts that terminate or allow price renegotiation on change of control.\n"
        "- Unusual revenue recognition timing relative to contract milestones.\n"
        "- High churn or NRR below 100% in a SaaS business masking revenue quality issues.\n"
        "- Pending customer disputes, chargebacks, or warranty claims above reserve levels.\n"
        "- Government or regulated customer contracts with additional approval requirements post-close."
    ),
    AgentName.REPUTATION: (
        "- Adverse media coverage — bribery, fraud, misconduct, or regulatory censure in the last 5 years.\n"
        "- Whistleblower reports filed internally or with regulators that remain unresolved.\n"
        "- Involvement in ESG controversies — child labour, illegal dumping, discrimination settlements.\n"
        "- Social media crises or brand boycotts that have materially affected revenue.\n"
        "- Executives or board members with prior debarment, criminal convictions, or SEC sanctions.\n"
        "- Association with politically exposed persons (PEPs) or entities on watchlists."
    ),
    AgentName.ESG: (
        "- Environmental remediation obligations for contaminated land or water systems.\n"
        "- Greenhouse gas emissions exceeding sector benchmarks or regulatory caps.\n"
        "- Hazardous waste disposal non-compliance — permits, manifests, or disposal site liability.\n"
        "- Supply chain human rights risks flagged under mandatory due diligence legislation.\n"
        "- Greenwashing exposure — ESG disclosures not backed by audited data.\n"
        "- Carbon credit or offset schemes that may be invalidated by regulatory change."
    ),
}


# ---------------------------------------------------------------------------
# Per-agent off-task discard rules
# ---------------------------------------------------------------------------

DISCARD_RULES: dict[AgentName, str] = {
    AgentName.IP: (
        "- Do NOT flag general commercial terms, pricing, or service-level agreements.\n"
        "- Do NOT flag employment terms unless they contain IP assignment clauses.\n"
        "- Do NOT flag data privacy issues — those belong to the Privacy agent.\n"
        "- Do NOT flag software licensing unless it creates IP ownership ambiguity."
    ),
    AgentName.LITIGATION: (
        "- Do NOT flag regulatory compliance issues — those belong to the Regulatory agent.\n"
        "- Do NOT flag contract terms that merely mention dispute resolution procedures without pending or threatened claims.\n"
        "- Do NOT flag insurance coverage gaps — those belong to the Insurance agent.\n"
        "- Do NOT flag tax disputes unless they involve active litigation."
    ),
    AgentName.REGULATORY: (
        "- Do NOT flag general contract terms, commercial pricing, or operational matters.\n"
        "- Do NOT flag tax provisions — those belong to the Tax agent.\n"
        "- Do NOT flag data privacy regulation — those belong to the Privacy agent.\n"
        "- Do NOT flag insurance requirements — those belong to the Insurance agent."
    ),
    AgentName.PRIVACY: (
        "- Do NOT flag cybersecurity infrastructure or IT system issues — those belong to the Cyber agent.\n"
        "- Do NOT flag general regulatory compliance — those belong to the Regulatory agent.\n"
        "- Do NOT flag HR or employment terms unless they involve personal data processing.\n"
        "- Do NOT flag general contract confidentiality clauses that do not involve personal data."
    ),
    AgentName.FINANCE: (
        "- Do NOT flag tax provisions — those belong to the Tax agent.\n"
        "- Do NOT flag insurance premiums or policy terms — those belong to the Insurance agent.\n"
        "- Do NOT flag employment compensation details — those belong to the HR agent.\n"
        "- Do NOT flag IP valuation unless it directly affects balance sheet items."
    ),
    AgentName.TAX: (
        "- Do NOT flag general financial statements unless they contain specific tax provisions.\n"
        "- Do NOT flag employment terms unless they involve tax withholding or benefits tax treatment.\n"
        "- Do NOT flag regulatory compliance — those belong to the Regulatory agent.\n"
        "- Do NOT flag insurance premium deductibility — those belong to the Finance agent."
    ),
    AgentName.INSURANCE: (
        "- Do NOT flag litigation or legal claims — those belong to the Litigation agent.\n"
        "- Do NOT flag financial covenants or debt instruments — those belong to the Finance agent.\n"
        "- Do NOT flag cybersecurity controls — those belong to the Cyber agent.\n"
        "- Do NOT flag regulatory permits or licences — those belong to the Regulatory agent."
    ),
    AgentName.HR: (
        "- Do NOT flag IP assignment — those belong to the IP agent.\n"
        "- Do NOT flag pension fund investment performance — those belong to the Finance agent.\n"
        "- Do NOT flag data privacy in HR systems — those belong to the Privacy agent.\n"
        "- Do NOT flag board governance or shareholder rights — those belong to the Governance agent."
    ),
    AgentName.GOVERNANCE: (
        "- Do NOT flag employment contracts or HR matters — those belong to the HR agent.\n"
        "- Do NOT flag regulatory filings or permits — those belong to the Regulatory agent.\n"
        "- Do NOT flag related party transactions — those belong to the Related Party agent.\n"
        "- Do NOT flag financial statement analysis — those belong to the Finance agent."
    ),
    AgentName.RELATED_PARTY: (
        "- Do NOT flag arm's-length commercial contracts with unrelated parties.\n"
        "- Do NOT flag standard vendor or supplier agreements — those belong to the Supplier agent.\n"
        "- Do NOT flag board governance procedures — those belong to the Governance agent.\n"
        "- Do NOT flag employment terms for non-related-party employees — those belong to the HR agent."
    ),
    AgentName.CYBER: (
        "- Do NOT flag data privacy regulatory compliance (GDPR, CCPA) — those belong to the Privacy agent.\n"
        "- Do NOT flag IP ownership of software — those belong to the IP agent.\n"
        "- Do NOT flag general insurance coverage — those belong to the Insurance agent.\n"
        "- Do NOT flag physical asset security — those belong to the Assets agent."
    ),
    AgentName.ASSETS: (
        "- Do NOT flag IP or intangible asset ownership disputes — those belong to the IP agent.\n"
        "- Do NOT flag supplier contracts or procurement — those belong to the Supplier agent.\n"
        "- Do NOT flag financial valuation methodologies — those belong to the Finance agent.\n"
        "- Do NOT flag ESG environmental contamination — those belong to the ESG agent."
    ),
    AgentName.SUPPLIER: (
        "- Do NOT flag customer contracts or revenue concentration — those belong to the Customer agent.\n"
        "- Do NOT flag employment of supplier personnel — those belong to the HR agent.\n"
        "- Do NOT flag related party transactions — those belong to the Related Party agent.\n"
        "- Do NOT flag insurance requirements in supplier contracts — those belong to the Insurance agent."
    ),
    AgentName.CUSTOMER: (
        "- Do NOT flag supplier contracts or procurement terms — those belong to the Supplier agent.\n"
        "- Do NOT flag data privacy obligations in customer contracts — those belong to the Privacy agent.\n"
        "- Do NOT flag IP licensing to customers — those belong to the IP agent.\n"
        "- Do NOT flag accounts payable — those belong to the Finance agent."
    ),
    AgentName.REPUTATION: (
        "- Do NOT flag regulatory compliance failures — those belong to the Regulatory agent.\n"
        "- Do NOT flag pending litigation specifics — those belong to the Litigation agent.\n"
        "- Do NOT flag ESG environmental issues — those belong to the ESG agent.\n"
        "- Do NOT flag financial misstatements — those belong to the Finance agent."
    ),
    AgentName.ESG: (
        "- Do NOT flag general regulatory compliance — those belong to the Regulatory agent.\n"
        "- Do NOT flag reputational media coverage — those belong to the Reputation agent.\n"
        "- Do NOT flag physical asset conditions unrelated to environmental risk — those belong to the Assets agent.\n"
        "- Do NOT flag insurance for environmental liability — those belong to the Insurance agent."
    ),
}


class SpecialistAgent(BaseSpecialistAgent):
    """Concrete specialist agent parameterized by ``SpecialistDefinition``.

    All 16 specialist agents are instances of this single class,
    differentiated only by their routing terms, synonym groups,
    clause_type filters, domain description, domain instructions,
    and off-task discard rules.
    """

    @property
    def _domain_description(self) -> str:
        return DOMAIN_DESCRIPTIONS.get(
            self.agent_name,
            f"{self.agent_name.value} domain analysis",
        )

    @property
    def _domain_instructions(self) -> str:
        return DOMAIN_INSTRUCTIONS.get(self.agent_name, "")

    @property
    def _discard_rules(self) -> str:
        return DISCARD_RULES.get(self.agent_name, "")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_specialist_agents(
    manifest: ActiveSpecialistManifest,
    search_engine: SparseSearchEngine,
    llm_client: LLMClientProtocol,
    *,
    registry: list[SpecialistDefinition] | None = None,
) -> list[SpecialistAgent]:
    """Create ``SpecialistAgent`` instances for each active agent in the manifest.

    Parameters
    ----------
    manifest:
        Planner output listing which agents should run.
    search_engine:
        Injected Elasticsearch BM25 search engine.
    llm_client:
        Injected LLM client (Ollama or mock).
    registry:
        Optional specialist registry override for testing.
        Defaults to ``SPECIALIST_REGISTRY`` from the planner module.
    """

    from src.agents.planner_agent import SPECIALIST_REGISTRY

    source = registry if registry is not None else SPECIALIST_REGISTRY
    definitions_by_name = {defn.agent_name: defn for defn in source}
    agents: list[SpecialistAgent] = []

    for agent_name in manifest.active_agents:
        defn = definitions_by_name.get(agent_name)
        if defn is None:
            continue
        agents.append(SpecialistAgent(defn, search_engine, llm_client))

    return agents
