# Migration Guide

## Deployment Strategy

### Blue-Green Deployment
To ensure zero downtime during the migration from Groq to the new multi-provider architecture:

1.  **Deploy "Green" Environment**:
    - Deploy the new version of the application with `ENABLE_GROQ=true` and `PRIMARY_PROVIDER=groq` (initially) to the Green environment.
    - Run `tests/unit/test_model_migration.py` in the Green environment to verify new providers are functional.

2.  **Switch Traffic (Canary)**:
    - Route 10% of traffic to the Green environment.
    - Monitor error rates and latency.

3.  **Enable New Providers**:
    - In the Green environment, set `PRIMARY_PROVIDER=openrouter` and `PRIMARY_STT_PROVIDER=openai` (or `local`).
    - Verify that Qwen and Whisper models are processing requests correctly.

4.  **Full Cutover**:
    - If stable, route 100% of traffic to Green.
    - Green becomes the new Blue.

### Monitoring
Set up alerts for:
- **Error Rates**: > 1% failure rate on `/analyze` or `/transcribe` endpoints.
- **Latency**: > 5s increase in p95 response time.
- **Provider Status**: Monitor OpenRouter and OpenAI status pages.

## Rollback Procedures

### Automated Rollback Triggers
- **500 Error Rate spike**: If error rate exceeds 5% for 5 minutes.
- **Response Validation Failures**: If JSON validation fails for > 2% of requests (indicating model output issues).

### Manual Rollback
If critical issues arise with the new models:
1.  **Revert Configuration**:
    ```bash
    export PRIMARY_PROVIDER=groq
    export PRIMARY_STT_PROVIDER=groq
    export ENABLE_LOCAL_WHISPER=false
    ```
2.  **Restart Service**: Apply changes immediately.
3.  **Redeploy**: If code reversion is needed, checkout the previous tag.

## Post-Migration Validation

### A/B Testing
- **Control**: Groq (Llama 3.3 / Whisper V3 Turbo)
- **Variant**: OpenRouter (Qwen 2.5 / Whisper V3 Turbo Local)
- **Metrics**:
    - User Satisfaction (Thumb up/down)
    - Clinical Accuracy (Expert Review Sample)
    - Cost per transaction

### Optimization Iterations
1.  **Week 1**: Gather performance metrics. Identify slow queries.
2.  **Week 2**: Tune system prompts for Qwen 2.5 to improve JSON adherence.
3.  **Week 3**: Optimize Local Whisper beam size and device usage.

### Deprecation Timeline
- **Phase 1 (Now)**: Migration started. Groq is fallback.
- **Phase 2 (+2 Weeks)**: Groq disabled by default, enabled only via flag.
- **Phase 3 (+4 Weeks)**: Remove Groq code entirely.
