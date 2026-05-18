# Config Reference

## Search URLs (config.json → search.search_urls)
Array of LinkedIn search URLs. Bot processes each in order until max_applications is reached.

Current URLs target:
1. `senior java developer` — US, last 7 days, Easy Apply, salary $120k–$274k
2. `senior java full stack developer` — same filters
3. `senior spring boot developer` — same filters
4. `senior java backend developer` — same filters

### LinkedIn URL Parameters
| Param | Value | Meaning |
|-------|-------|---------|
| `keywords=` | URL-encoded role title | Job search keywords |
| `geoId=103644278` | US | Country filter |
| `distance=0.0` | any | Distance from location |
| `f_TPR=r604800` | 7 days | Time range (86400=1d, 604800=7d) |
| `f_AL=true` | — | Easy Apply only |
| `f_LF=f_AL` | — | Alternative Easy Apply param (older pages) |
| `f_JT=C` | Contract | Employment type (F=full-time, C=contract) |
| `f_WT=2` | Remote | Work type (1=onsite, 2=remote, 3=hybrid) |
| `f_SAL=f_SA_id_226001%3A274001` | $120k–$274k | Salary range |
| `sortBy=DD` | — | Most recent first |

## Title Filters
```json
"title_must_contain_one_of": ["java", "spring", "j2ee", "jvm", "full stack", "fullstack", "backend developer", "microservice", "api developer"]
"title_must_not_contain": [".net", "c#", "php", "ios", "android", "salesforce", "sap", "ruby", "golang", "react developer", "angular developer", "frontend developer", "ui developer", "python developer", "data engineer", "ml engineer", "devops engineer"]
```

## Years Map (_YEARS_MAP in claude_agent.py)
Known resume skills always return >= 5 years.
Related skills (angular, redis, postgresql) return 4-5.
Unknown skills return 1-2.

Key mappings:
- java: 8, spring_boot: 7, spring: 8
- react: 6, nodejs: 6, typescript: 5
- aws: 6, azure: 4, kubernetes: 5, docker: 6
- microservices: 7, sql: 8, kafka: 4
