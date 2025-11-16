"""
Compliance Engine for Regulatory Validation and Risk Assessment
Implements SOX, SEC, MiFID II, and Basel III compliance checks
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplianceStatus(Enum):
    """Compliance status enumeration"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplianceViolation:
    """Container for compliance violation"""
    violation_id: str
    regulation: str
    severity: str
    description: str
    requirement: str
    evidence: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class ComplianceReport:
    """Container for compliance report"""
    report_id: str
    document_id: str
    jurisdiction: str
    compliant: bool
    violations: List[ComplianceViolation]
    warnings: List[Dict[str, Any]]
    risk_scores: Dict[str, float]
    timestamp: datetime
    metadata: Dict[str, Any]


class SarbanesOxleyValidator:
    """
    Sarbanes-Oxley Act (SOX) compliance validator
    """

    def __init__(self):
        self.requirements = {
            'internal_controls': 'Section 302 - Internal Controls',
            'financial_accuracy': 'Section 404 - Management Assessment',
            'audit_committee': 'Section 301 - Audit Committee',
            'officer_certification': 'Section 302 - CEO/CFO Certification'
        }

    def validate(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate SOX compliance
        """
        logger.info("Performing SOX compliance validation")

        violations = []
        warnings = []

        # Check for officer certification
        if not self._check_officer_certification(report):
            violations.append(ComplianceViolation(
                violation_id="SOX_302_001",
                regulation="SOX Section 302",
                severity="HIGH",
                description="Missing officer certification",
                requirement="CEO/CFO must certify financial statements",
                recommendation="Include signed officer certification"
            ))

        # Check internal controls disclosure
        if not self._check_internal_controls(report):
            warnings.append({
                'code': 'SOX_404_001',
                'message': 'Internal controls assessment may be incomplete',
                'section': 'Section 404'
            })

        # Check audit committee independence
        if not self._check_audit_committee(report):
            warnings.append({
                'code': 'SOX_301_001',
                'message': 'Audit committee independence not verified',
                'section': 'Section 301'
            })

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings
        }

    def _check_officer_certification(self, report: Dict[str, Any]) -> bool:
        """Check for officer certification"""
        content = report.get('content', '').lower()
        keywords = ['certify', 'certification', 'officer certification', 'ceo', 'cfo']

        return any(keyword in content for keyword in keywords)

    def _check_internal_controls(self, report: Dict[str, Any]) -> bool:
        """Check internal controls disclosure"""
        content = report.get('content', '').lower()
        keywords = ['internal control', 'control environment', 'icfr']

        return any(keyword in content for keyword in keywords)

    def _check_audit_committee(self, report: Dict[str, Any]) -> bool:
        """Check audit committee disclosure"""
        content = report.get('content', '').lower()
        keywords = ['audit committee', 'independent director', 'committee charter']

        return any(keyword in content for keyword in keywords)


class SECComplianceChecker:
    """
    SEC filing compliance checker
    """

    def __init__(self):
        self.required_sections = {
            '10-K': [
                'business',
                'risk factors',
                'financial data',
                'md&a',
                'financial statements',
                'controls and procedures'
            ],
            '10-Q': [
                'financial statements',
                'md&a',
                'controls and procedures'
            ],
            '8-K': [
                'item number',
                'event description'
            ]
        }

    def validate(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate SEC filing compliance
        """
        logger.info("Performing SEC compliance validation")

        doc_type = report.get('document_type', '').upper()
        violations = []
        warnings = []

        if doc_type not in self.required_sections:
            return {
                'compliant': True,
                'violations': [],
                'warnings': [{
                    'code': 'SEC_001',
                    'message': f'Unknown document type: {doc_type}'
                }]
            }

        # Check required sections
        required = self.required_sections[doc_type]
        missing_sections = self._check_required_sections(report, required)

        for section in missing_sections:
            violations.append(ComplianceViolation(
                violation_id=f"SEC_{doc_type}_SECTION",
                regulation=f"SEC {doc_type} Requirements",
                severity="HIGH",
                description=f"Missing required section: {section}",
                requirement=f"{doc_type} must include {section}",
                recommendation=f"Add {section} section to filing"
            ))

        # Check filing timeliness
        if not self._check_filing_timeliness(report, doc_type):
            violations.append(ComplianceViolation(
                violation_id="SEC_TIMELINESS",
                regulation="SEC Filing Deadlines",
                severity="MEDIUM",
                description="Filing may be late",
                requirement=f"{doc_type} filing deadlines per SEC rules",
                recommendation="Review filing timeline"
            ))

        # Check XBRL tagging (for modern filings)
        if not self._check_xbrl_compliance(report):
            warnings.append({
                'code': 'SEC_XBRL',
                'message': 'XBRL tagging may be incomplete or missing'
            })

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings
        }

    def _check_required_sections(
        self,
        report: Dict[str, Any],
        required_sections: List[str]
    ) -> List[str]:
        """Check for required sections"""
        content = report.get('content', '').lower()
        missing = []

        for section in required_sections:
            if section.lower() not in content:
                missing.append(section)

        return missing

    def _check_filing_timeliness(
        self,
        report: Dict[str, Any],
        doc_type: str
    ) -> bool:
        """
        Check if filing is timely
        """
        filing_date = report.get('filing_date')
        period_end = report.get('period_end_date')

        if not filing_date or not period_end:
            return True  # Cannot verify, give benefit of doubt

        # Simplified timeliness check
        # 10-K: within 90 days of fiscal year end
        # 10-Q: within 45 days of quarter end

        if isinstance(filing_date, datetime) and isinstance(period_end, datetime):
            days_diff = (filing_date - period_end).days

            if doc_type == '10-K':
                return days_diff <= 90
            elif doc_type == '10-Q':
                return days_diff <= 45

        return True

    def _check_xbrl_compliance(self, report: Dict[str, Any]) -> bool:
        """Check XBRL tagging compliance"""
        # Simplified check
        content = report.get('content', '')
        return 'xbrl' in content.lower() or 'xml' in content.lower()


class MiFIDValidator:
    """
    MiFID II compliance validator (European markets)
    """

    def __init__(self):
        self.requirements = {
            'transparency': 'Transparency requirements',
            'best_execution': 'Best execution reporting',
            'investor_protection': 'Investor protection measures'
        }

    def validate(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate MiFID II compliance
        """
        logger.info("Performing MiFID II compliance validation")

        # Simplified MiFID validation
        violations = []
        warnings = []

        # Check transparency requirements
        if not self._check_transparency(report):
            warnings.append({
                'code': 'MIFID_TRANSPARENCY',
                'message': 'Transparency requirements may not be fully met'
            })

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings
        }

    def _check_transparency(self, report: Dict[str, Any]) -> bool:
        """Check transparency requirements"""
        content = report.get('content', '').lower()
        keywords = ['disclosure', 'transparent', 'transparency']

        return any(keyword in content for keyword in keywords)


class BaselIIIChecker:
    """
    Basel III compliance checker (for banks)
    """

    def __init__(self):
        self.min_capital_ratios = {
            'cet1': 4.5,  # Common Equity Tier 1
            'tier1': 6.0,  # Total Tier 1
            'total_capital': 8.0  # Total Capital
        }

    def validate(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Basel III compliance
        """
        logger.info("Performing Basel III compliance validation")

        violations = []
        warnings = []

        # Check capital adequacy ratios
        capital_ratios = self._extract_capital_ratios(report)

        for ratio_type, min_ratio in self.min_capital_ratios.items():
            if ratio_type in capital_ratios:
                if capital_ratios[ratio_type] < min_ratio:
                    violations.append(ComplianceViolation(
                        violation_id=f"BASEL_{ratio_type.upper()}",
                        regulation="Basel III Capital Requirements",
                        severity="CRITICAL",
                        description=f"{ratio_type.upper()} ratio below minimum",
                        requirement=f"Minimum {min_ratio}%",
                        evidence=f"Current ratio: {capital_ratios[ratio_type]}%"
                    ))

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings
        }

    def _extract_capital_ratios(self, report: Dict[str, Any]) -> Dict[str, float]:
        """Extract capital ratios from report"""
        # Simplified extraction
        # In production, parse actual financial tables

        ratios = {}

        content = report.get('content', '').lower()

        # Look for CET1 ratio
        import re
        cet1_pattern = r'cet1.*?(\d+\.?\d*)%'
        match = re.search(cet1_pattern, content)
        if match:
            ratios['cet1'] = float(match.group(1))

        return ratios


class RiskAssessmentEngine:
    """
    Comprehensive risk assessment engine
    """

    def __init__(self):
        self.risk_weights = {
            'credit_risk': 0.25,
            'market_risk': 0.25,
            'operational_risk': 0.20,
            'liquidity_risk': 0.20,
            'regulatory_risk': 0.10
        }

    def assess_credit_risk(self, report: Dict[str, Any]) -> float:
        """Assess credit risk"""
        # Simplified credit risk assessment
        # Look for credit-related keywords

        content = report.get('content', '').lower()

        risk_keywords = {
            'default': 0.3,
            'bad debt': 0.3,
            'credit loss': 0.25,
            'impairment': 0.2,
            'delinquent': 0.25
        }

        risk_score = 0.0
        for keyword, weight in risk_keywords.items():
            if keyword in content:
                risk_score += weight

        return min(risk_score, 1.0)

    def assess_market_risk(self, report: Dict[str, Any]) -> float:
        """Assess market risk"""
        content = report.get('content', '').lower()

        risk_keywords = {
            'market volatility': 0.3,
            'price risk': 0.25,
            'interest rate risk': 0.3,
            'currency risk': 0.2,
            'commodity risk': 0.2
        }

        risk_score = 0.0
        for keyword, weight in risk_keywords.items():
            if keyword in content:
                risk_score += weight

        return min(risk_score, 1.0)

    def assess_operational_risk(self, report: Dict[str, Any]) -> float:
        """Assess operational risk"""
        content = report.get('content', '').lower()

        risk_keywords = {
            'operational failure': 0.4,
            'system failure': 0.3,
            'fraud': 0.4,
            'cyber': 0.35,
            'business disruption': 0.25
        }

        risk_score = 0.0
        for keyword, weight in risk_keywords.items():
            if keyword in content:
                risk_score += weight

        return min(risk_score, 1.0)

    def assess_liquidity_risk(self, report: Dict[str, Any]) -> float:
        """Assess liquidity risk"""
        content = report.get('content', '').lower()

        risk_keywords = {
            'liquidity crisis': 0.4,
            'cash shortage': 0.35,
            'funding risk': 0.3,
            'working capital': 0.15
        }

        risk_score = 0.0
        for keyword, weight in risk_keywords.items():
            if keyword in content:
                risk_score += weight

        return min(risk_score, 1.0)

    def assess_regulatory_risk(self, report: Dict[str, Any]) -> float:
        """Assess regulatory risk"""
        content = report.get('content', '').lower()

        risk_keywords = {
            'regulatory investigation': 0.4,
            'compliance violation': 0.35,
            'litigation': 0.25,
            'penalty': 0.3,
            'enforcement action': 0.4
        }

        risk_score = 0.0
        for keyword, weight in risk_keywords.items():
            if keyword in content:
                risk_score += weight

        return min(risk_score, 1.0)


class ComplianceEngine:
    """
    Main compliance engine coordinating all validators
    """

    def __init__(self):
        self.regulations = {
            'sox': SarbanesOxleyValidator(),
            'sec': SECComplianceChecker(),
            'mifid2': MiFIDValidator(),
            'basel3': BaselIIIChecker()
        }
        self.risk_assessor = RiskAssessmentEngine()

        logger.info("Initialized ComplianceEngine")

    def validate_financial_report(
        self,
        report: Dict[str, Any],
        jurisdiction: str = 'US'
    ) -> ComplianceReport:
        """
        Comprehensive compliance validation
        """
        logger.info(f"Validating report: {report.get('document_id')} ({jurisdiction})")

        all_violations = []
        all_warnings = []

        # SEC compliance (US)
        if jurisdiction == 'US':
            sec_result = self.regulations['sec'].validate(report)
            all_violations.extend(sec_result['violations'])
            all_warnings.extend(sec_result['warnings'])

            # SOX compliance
            sox_result = self.regulations['sox'].validate(report)
            all_violations.extend(sox_result['violations'])
            all_warnings.extend(sox_result['warnings'])

        # MiFID II (EU)
        elif jurisdiction == 'EU':
            mifid_result = self.regulations['mifid2'].validate(report)
            all_violations.extend(mifid_result['violations'])
            all_warnings.extend(mifid_result['warnings'])

        # Risk assessment
        risk_scores = self._assess_all_risks(report)

        # Generate report
        compliance_report = ComplianceReport(
            report_id=f"compliance_{report.get('document_id')}_{datetime.now().timestamp()}",
            document_id=report.get('document_id', ''),
            jurisdiction=jurisdiction,
            compliant=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings,
            risk_scores=risk_scores,
            timestamp=datetime.now(),
            metadata={
                'num_violations': len(all_violations),
                'num_warnings': len(all_warnings),
                'overall_risk': risk_scores.get('composite', 0.0)
            }
        )

        logger.info(f"Compliance validation complete. Compliant: {compliance_report.compliant}")

        return compliance_report

    def _assess_all_risks(self, report: Dict[str, Any]) -> Dict[str, float]:
        """
        Assess all risk categories
        """
        risks = {
            'credit_risk': self.risk_assessor.assess_credit_risk(report),
            'market_risk': self.risk_assessor.assess_market_risk(report),
            'operational_risk': self.risk_assessor.assess_operational_risk(report),
            'liquidity_risk': self.risk_assessor.assess_liquidity_risk(report),
            'regulatory_risk': self.risk_assessor.assess_regulatory_risk(report)
        }

        # Calculate composite risk score
        composite = sum(
            risks[risk_type] * weight
            for risk_type, weight in self.risk_assessor.risk_weights.items()
        )

        risks['composite'] = composite

        return risks

    def generate_compliance_summary(
        self,
        compliance_report: ComplianceReport
    ) -> str:
        """
        Generate human-readable compliance summary
        """
        summary_parts = []

        summary_parts.append(f"Compliance Report for {compliance_report.document_id}")
        summary_parts.append(f"Jurisdiction: {compliance_report.jurisdiction}")
        summary_parts.append(f"Status: {'COMPLIANT' if compliance_report.compliant else 'NON-COMPLIANT'}")
        summary_parts.append(f"\nViolations: {len(compliance_report.violations)}")

        for violation in compliance_report.violations:
            summary_parts.append(f"  - [{violation.severity}] {violation.description}")

        summary_parts.append(f"\nWarnings: {len(compliance_report.warnings)}")

        summary_parts.append(f"\nRisk Assessment:")
        for risk_type, score in compliance_report.risk_scores.items():
            summary_parts.append(f"  - {risk_type}: {score:.2f}")

        return "\n".join(summary_parts)
