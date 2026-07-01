from extensions import db
from common.models.Predefined_skills import PredefinedSkill

def seed_predefined_skills():
    skills = [

        # Programming Languages
        "Python", "Java", "C", "C++", "C#", "Go", "Rust",
        "JavaScript", "TypeScript", "Kotlin", "Swift",
        "PHP", "Ruby", "Scala", "R", "MATLAB",

        # Backend Frameworks
        "Django", "Flask", "FastAPI",
        "Spring Boot", "Spring MVC",
        "Node.js", "Express.js", "NestJS",
        "Ruby on Rails", "ASP.NET Core",
        "Laravel",

        # Frontend
        "React", "Next.js", "Vue.js", "Nuxt.js",
        "Angular", "Svelte",
        "HTML", "CSS", "Tailwind CSS",
        "Bootstrap", "Material UI",

        # Mobile
        "Flutter", "React Native",
        "Android", "iOS",
        "SwiftUI", "Kotlin Multiplatform",

        # Databases
        "MySQL", "PostgreSQL", "MongoDB",
        "Redis", "SQLite",
        "Oracle", "SQL Server",
        "Cassandra", "DynamoDB",

        # DevOps & Cloud
        "AWS", "Azure", "Google Cloud",
        "Docker", "Kubernetes",
        "Terraform", "Ansible",
        "CI/CD", "GitHub Actions",
        "Jenkins", "GitLab CI",

        # Version Control
        "Git", "GitHub", "GitLab", "Bitbucket",

        # APIs & Architecture
        "REST API", "GraphQL",
        "Microservices", "Monolith Architecture",
        "Event-Driven Architecture",
        "WebSockets",

        # Testing
        "PyTest", "JUnit",
        "Selenium", "Cypress",
        "Unit Testing", "Integration Testing",
        "TDD", "BDD",

        # Data & AI
        "Machine Learning",
        "Deep Learning",
        "Data Science",
        "Pandas", "NumPy",
        "TensorFlow", "PyTorch",
        "Scikit-learn",
        "NLP",
        "Computer Vision",
        "LLM", "LangChain",
        "OpenAI API",

        # Big Data
        "Hadoop", "Spark",
        "Kafka", "Airflow",
        "Snowflake", "Databricks",

        # Security
        "Cybersecurity",
        "OAuth",
        "JWT",
        "Penetration Testing",
        "OWASP",

        # UI/UX
        "Figma",
        "Adobe XD",
        "UI Design",
        "UX Research",

        # System Design
        "System Design",
        "Scalability",
        "Load Balancing",
        "Caching",
        "CDN",

        # Others
        "Linux",
        "Bash",
        "Shell Scripting",
        "Networking",
        "Agile",
        "Scrum",
        "JIRA"
    ]

    for skill in skills:

        skill_name = skill.strip()
        normalized_name = skill_name.lower()

        exists = PredefinedSkill.query.filter_by(
            normalized_name=normalized_name,
            org_id=None
        ).first()

        if not exists:

            db.session.add(
                PredefinedSkill(
                    name=skill_name,
                    normalized_name=normalized_name,
                    org_id=None,
                    is_active=True,
                    created_by_user=False
                )
            )

    db.session.commit()
    print("Predefined skills seeded successfully!")