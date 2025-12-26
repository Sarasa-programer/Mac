# Migration Checklist Template

Use this checklist when working on the migration from Groq to independent providers.

## Pre-Migration

- [ ] Review `MIGRATION_PLAN.md`
- [ ] Set up API keys (OpenRouter, OpenAI)
- [ ] Configure environment variables
- [ ] Review feature flags
- [ ] Test provider connectivity

## Code Migration

- [ ] Update service to use `LLMProviderFactory`
- [ ] Update service to use `TranscriptionProviderFactory`
- [ ] Remove direct Groq dependencies
- [ ] Add fallback error handling
- [ ] Update configuration files
- [ ] Test locally

## Testing

- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Performance benchmarking
- [ ] Error scenarios tested

## Deployment

- [ ] Deploy to staging
- [ ] Monitor for 24-48 hours
- [ ] Validate metrics
- [ ] Plan production rollout
- [ ] Execute canary deployment
- [ ] Monitor production metrics

## Post-Deployment

- [ ] Monitor for 1 week
- [ ] Gather user feedback
- [ ] Performance analysis
- [ ] Cost analysis
- [ ] Documentation updates

