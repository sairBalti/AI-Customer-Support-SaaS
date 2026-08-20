"""Generate Saira Batool resume PDF (ATS-friendly, 2 pages)."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = Path(__file__).resolve().parent
PDF_PATH = OUT_DIR / "Saira_Batool_Resume.pdf"

NAVY = HexColor("#0F2744")
TEAL = HexColor("#0E7490")
BODY = HexColor("#1A1A1A")
MUTED = HexColor("#444444")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "Name",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=NAVY,
            alignment=1,
            spaceAfter=1,
        ),
        "headline": ParagraphStyle(
            "Headline",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=TEAL,
            alignment=1,
            spaceAfter=4,
        ),
        "contact": ParagraphStyle(
            "Contact",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=BODY,
            alignment=1,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=NAVY,
            spaceBefore=6,
            spaceAfter=2,
            textTransform="uppercase",
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=BODY,
            alignment=4,
            spaceAfter=4,
        ),
        "skill": ParagraphStyle(
            "Skill",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=12.4,
            textColor=BODY,
            spaceAfter=2,
        ),
        "jobtitle": ParagraphStyle(
            "JobTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=NAVY,
        ),
        "dates": ParagraphStyle(
            "Dates",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=MUTED,
            alignment=2,
        ),
        "org": ParagraphStyle(
            "Org",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=12,
            textColor=BODY,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=12.2,
            textColor=BODY,
        ),
        "proj": ParagraphStyle(
            "Proj",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.4,
            leading=13,
            textColor=NAVY,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=BODY,
            spaceAfter=1,
        ),
        "edu": ParagraphStyle(
            "Edu",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=BODY,
        ),
    }


def hr() -> HRFlowable:
    return HRFlowable(width="100%", thickness=1.15, color=NAVY, spaceBefore=0, spaceAfter=4)


def bullets(s: dict[str, ParagraphStyle], items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, s["bullet"]), leftIndent=8, bulletColor=NAVY) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=14,
        bulletFontName="Helvetica",
        bulletFontSize=10,
        spaceBefore=0,
        spaceAfter=2,
    )


def job_head(s: dict[str, ParagraphStyle], title: str, dates: str) -> Table:
    t = Table(
        [[Paragraph(title, s["jobtitle"]), Paragraph(dates, s["dates"])]],
        colWidths=[5.5 * inch, 1.85 * inch],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def edu_row(s: dict[str, ParagraphStyle], left: str, dates: str) -> Table:
    t = Table(
        [[Paragraph(left, s["edu"]), Paragraph(dates, s["dates"])]],
        colWidths=[5.5 * inch, 1.85 * inch],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return t


def build() -> None:
    s = styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=0.62 * inch,
        rightMargin=0.62 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.42 * inch,
        title="Saira Batool — Resume",
        author="Saira Batool",
    )
    story: list = []

    story.append(Paragraph("SAIRA BATOOL", s["name"]))
    story.append(
        Paragraph(
            "Full-Stack SaaS Engineer | ERP &amp; Multi-Tenant Systems | Agentic AI &amp; Workflow Automation",
            s["headline"],
        )
    )
    story.append(
        Paragraph(
            '<link href="mailto:ssairabatool98@gmail.com">ssairabatool98@gmail.com</link>'
            "  |  "
            '<link href="https://www.linkedin.com/in/saira-batool">linkedin.com/in/saira-batool</link>'
            "  |  Pakistan",
            s["contact"],
        )
    )

    story.append(Paragraph("PROFESSIONAL SUMMARY", s["h2"]))
    story.append(hr())
    story.append(
        Paragraph(
            "Full-Stack SaaS Engineer with 4+ years of experience building production web applications, "
            "multi-tenant ERP/SaaS systems, REST APIs, and business workflow automation. Delivers full-stack "
            "products using Python, FastAPI, React, Node.js, and MySQL, with practical work in authentication, "
            "RBAC, and administrative dashboards. Hands-on with Agentic AI and LLM-powered applications, "
            "including RAG-based knowledge retrieval, AI customer support, and automated ticket/escalation "
            "workflows. Complements product engineering with strong QA automation: Pytest, Selenium, Playwright, "
            "API automation, and CI/CD (GitHub Actions, Azure DevOps, Jenkins). Focused on reliable, testable, "
            "production-quality software.",
            s["body"],
        )
    )

    story.append(Paragraph("CORE EXPERTISE", s["h2"]))
    story.append(hr())
    story.append(
        Paragraph(
            "<b>SaaS &amp; ERP Engineering:</b> Multi-Tenant SaaS Architecture · ERP Application Development · "
            "Role-Based Access Control · Authentication &amp; Authorization · Business Workflow Systems · Admin Dashboards",
            s["skill"],
        )
    )
    story.append(
        Paragraph(
            "<b>Agentic AI &amp; Automation:</b> AI Agents · Agentic Workflows · LLM-Powered Applications · RAG · "
            "AI Customer Support · Business Workflow Automation",
            s["skill"],
        )
    )
    story.append(
        Paragraph(
            "<b>Full-Stack Engineering:</b> Python · FastAPI · React · Next.js · Node.js · Express.js · REST APIs · "
            "MySQL · SQL Server · .NET Core · C# · JavaScript · HTML5 · CSS3 · Tailwind CSS",
            s["skill"],
        )
    )
    story.append(
        Paragraph(
            "<b>QA &amp; Test Automation:</b> Pytest · Selenium · Playwright · Cypress · Appium · API Automation · "
            "E2E Testing · Integration Testing · Performance Testing · JMeter",
            s["skill"],
        )
    )
    story.append(
        Paragraph(
            "<b>DevOps &amp; Engineering:</b> Git · GitHub · GitHub Actions · Azure DevOps · Jenkins · CI/CD · Docker · AWS",
            s["skill"],
        )
    )

    story.append(Paragraph("EXPERIENCE", s["h2"]))
    story.append(hr())

    story.append(job_head(s, "Software Test Engineer", "Jan 2024 – Present"))
    story.append(Paragraph("Technevity Inc · Shigar", s["org"]))
    story.append(
        bullets(
            s,
            [
                "Architected and implemented end-to-end web test automation frameworks from scratch using Python, Pytest, and Selenium for the CareKnox compliance/scheduling portal and ShiftKnox/Shift Portal.",
                "Designed reusable, scalable automation architecture covering smoke, regression, integration, and E2E testing.",
                "Built API automation and validation for critical backend services.",
                "Engineered mobile automation with Appium and performance testing with JMeter; identified bottlenecks and validated API response-time improvements from ~30s to under 2s.",
                "Integrated automation suites into CI/CD pipelines in collaboration with DevOps teams, reducing manual testing effort by approximately 80%.",
                "Developed an AI-powered self-healing automation capability that detects changed or broken UI locators at runtime and recovers using alternative locator strategies.",
            ],
        )
    )

    story.append(job_head(s, "Full Stack Development — Part Time", "Jan 2023 – Jan 2025"))
    story.append(Paragraph("Lamstan Technologies · Skardu", s["org"]))
    story.append(
        bullets(
            s,
            [
                "Designed and developed a full-stack Fleet Management System using React, Tailwind CSS, Node.js, Express.js, REST APIs, and MySQL.",
                "Implemented authentication, role-based access control, CRUD operations via stored procedures, pagination, filtering, and dashboard analytics.",
                "Optimized application performance and implemented LLM-assisted CRUD workflows for create, edit, and status operations.",
                'Live Demo: <link href="https://fleetsupporter.vercel.app/">https://fleetsupporter.vercel.app/</link>',
            ],
        )
    )

    story.append(
        KeepTogether(
            [
                job_head(s, "Full Stack Developer — 6-Month Internship", "Jan 2021 – Jan 2022"),
                Paragraph("Softify Technologies · Rawalpindi, Pakistan", s["org"]),
                bullets(
                    s,
                    [
                        "Developed full-stack features using .NET Core, C#, Razor Pages, REST APIs, and SQL Server.",
                        "Designed database models with Entity Framework Core (Code First) and implemented CRUD operations.",
                        "Built user-facing interfaces in HTML, CSS, C#, and Razor Pages integrated with backend APIs.",
                    ],
                ),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                job_head(s, "Junior Full Stack Developer", "Jan 2022 (2 months)"),
                Paragraph("Creative Garage · Islamabad, Pakistan", s["org"]),
                bullets(
                    s,
                    [
                        "Contributed to frontend and backend development using .NET technologies and SQL Server.",
                        "Built database-driven features and integrated user interfaces with server-side logic.",
                    ],
                ),
            ]
        )
    )

    story.append(Paragraph("SELECTED PROJECTS", s["h2"]))
    story.append(hr())

    story.append(
        KeepTogether(
            [
                Paragraph("BuildMind ERP — Multi-Tenant SaaS ERP Platform", s["proj"]),
                Paragraph(
                    'Live Demo: <link href="https://buildmind-cc.vercel.app/">https://buildmind-cc.vercel.app/</link>',
                    s["meta"],
                ),
                bullets(
                    s,
                    [
                        "Designed and developed a scalable multi-tenant SaaS ERP platform with company onboarding, role-based access control, user management, business workflows, REST APIs, administrative dashboards, and automated testing.",
                    ],
                ),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                Paragraph("AI Customer Support Agent — Agentic AI &amp; Workflow Automation", s["proj"]),
                Paragraph(
                    'Live Demo: <link href="https://supportpilot-saas.vercel.app/">https://supportpilot-saas.vercel.app/</link>',
                    s["meta"],
                ),
                bullets(
                    s,
                    [
                        "Designed and developed an AI-powered customer support platform using Python, FastAPI, React, REST APIs, and MySQL. Implemented LLM-powered agent workflows with RAG-based document retrieval to answer customer queries, create support tickets, and escalate complex issues to human agents (human-in-the-loop).",
                    ],
                ),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                Paragraph("AI Self-Healing Test Automation Framework", s["proj"]),
                bullets(
                    s,
                    [
                        "Built an AI-powered self-healing automation capability that detects broken or changed UI locators at runtime and identifies alternative locator strategies to improve automation resilience and reduce test maintenance (Python, Pytest, Selenium).",
                    ],
                ),
            ]
        )
    )

    story.append(
        KeepTogether(
            [
                Paragraph("Finger Spelling Detection Using Machine Learning", s["proj"]),
                Paragraph("University of Baltistan Skardu", s["meta"]),
                bullets(
                    s,
                    [
                        "Built a hand-gesture recognition system using OpenCV and MediaPipe landmark extraction; classified gestures with SVM and Random Forest and evaluated accuracy, precision, recall, and F1-score.",
                    ],
                ),
            ]
        )
    )

    story.append(Paragraph("EDUCATION", s["h2"]))
    story.append(hr())
    story.append(edu_row(s, "<b>BS Computer Science</b> — University of Baltistan Skardu", "2018 – 2021"))
    story.append(edu_row(s, "<b>Intermediate</b> — Girls Degree College Skardu", "2015 – 2017"))

    def on_page(canvas, doc_) -> None:
        canvas.saveState()
        canvas.setFillColor(white)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Wrote {PDF_PATH}")


if __name__ == "__main__":
    build()
