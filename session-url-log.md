# Session URL traversal log, 2026-07-06

Every external URL fetched (or attempted) during the Harnessie build session, reconstructed from the verification-workflow agent transcripts. URLs listed exactly as fetched (www forms preserved as traversal data). Verdicts for the charter sources live in [source-verification.json](source-verification.json).

## Charter sources, fetched and verified real (20)

- https://github.com/bybren-llc/safe-agentic-workflow
- https://harness-guide.com/guide/your-first-harness/
- https://github.com/nexu-io/harness-engineering-guide
- https://dev.to/thedailyagent/building-an-ai-agent-harness-from-scratch-the-architecture-between-llm-and-agent-5gg6
- https://www.ovrflo.studio/blog/how-to-build-your-own-ai-harness
- https://atlan.com/know/how-to-build-ai-agent-harness/
- https://dev.to/monuminu/harness-engineering-how-to-build-production-ready-llm-agents-that-actually-work-20kc
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- https://www.linkedin.com/pulse/how-actually-prompt-claude-fable-5-alphasignal-cckzf
- https://linas.substack.com/p/prompting-claude-fable-5-guide (free preview only; 12 patterns paywalled)
- https://lushbinary.com/blog/claude-fable-5-prompting-guide/ (WebFetch 403, fetched via browser-UA curl)
- https://conversionsystem.com/blog/how-to-prompt-claude-fable-5
- https://kbcafe.com/how-to-prompt-claude-fable-5
- https://huggingface.co/blog/Svngoku/claude-fable-5-technical-harness-report
- https://www.youtube.com/watch?v=vcU85OrwuV0 (watch page blocked; confirmed via oembed)
- https://lushbinary.com/blog/claude-fable-5-full-stack-app-development-guide/ (WebFetch 403, fetched via browser-UA curl)
- https://lushbinary.com/blog/claude-code-harness-every-task-dynamic-workflows-guide/ (WebFetch 403, fetched via browser-UA curl)
- https://www.youtube.com/watch?v=dJI2GRG1GEE (confirmed via oembed + search; also fetched with &themeRefresh=1 variant)
- https://github.com/coleam00/archon (also fetched as /Archon case variant)
- https://www.youtube.com/watch?v=qMnClynCAmM (confirmed via oembed + rendered page)

## Charter sources, attempted but unverifiable (2)

- https://www.facebook.com/groups/claudeaicommunity/posts/1317132990453865/ (login wall; verification agent died without verdict)
- https://www.youtube.com/watch?v=R_Nf-IDVZEg (bot wall; verification agent died without verdict; oembed attempted, result unrecorded)

## Official docs, fetched and confirmed loading (ground-truth pass)

- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview (302 redirect to the platform.claude.com equivalent)
- https://www.anthropic.com/news/claude-fable-5-mythos-5

## Cited by Perplexity, never fetched, existence unconfirmed

- https://anthropic.com/news/redeploying-fable-5

## Fetched by the harness-literature research agent (agent died before reporting; individual outcomes unrecorded)

- https://openai.com/index/harness-engineering/
- https://developers.openai.com/blog/harness-engineering
- https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- https://github.com/humanlayer/12-factor-agents
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://claude.com/blog/building-agents-with-the-claude-agent-sdk
- https://www.langchain.com/blog/on-agent-frameworks-and-agent-observability
- https://web.archive.org/web/2026/https://openai.com/index/harness-engineering/

## Helper and infrastructure endpoints

- https://api.perplexity.ai/chat/completions (sonar-pro queries; non-streaming requests dropped repeatedly, streaming succeeded)
- https://api.perplexity.ai (connectivity probe)
- https://www.youtube.com/oembed?url=... for video IDs vcU85OrwuV0, dJI2GRG1GEE, qMnClynCAmM, R_Nf-IDVZEg (title/author confirmation)
- https://duckduckgo.com/html/?q=... and https://html.duckduckgo.com/html/?q=... (search fallback for one video)
- https://r.jina.ai/https://www.youtube.com/watch?v=qMnClynCAmM (render mirror for one blocked watch page)
- https://lushbinary.com/ (homepage, crawl helper during the 403 workaround)

## Extraction false positives, never called

- https://api.anthropic.com/v1/messages, /v1/models/claude-opus-4-8, /v1/deployments: these appear inside transcripts only as curl examples quoted from fetched documentation pages; no agent executed a request against api.anthropic.com (verified against Bash tool-use records).
