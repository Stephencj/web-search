<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type CrawlJob } from '$lib/api/client';

  let jobs = $state<CrawlJob[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let statusFilter = $state<string>('');
  let activeCount = $state(0);

  onMount(() => {
    loadJobs();
    // Auto-refresh every 5 seconds if there are running jobs
    const interval = setInterval(() => {
      if (activeCount > 0) {
        loadJobs();
      }
    }, 5000);
    return () => clearInterval(interval);
  });

  async function loadJobs() {
    loading = true;
    error = null;
    try {
      const response = await api.getCrawlStatus(statusFilter || undefined, 50);
      jobs = response.jobs;
      activeCount = response.active_count || 0;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load crawl status';
    } finally {
      loading = false;
    }
  }

  async function stopJob(jobId: number) {
    try {
      await api.stopCrawl([jobId]);
      await loadJobs();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to stop crawl';
    }
  }

  async function stopAllJobs() {
    try {
      await api.stopCrawl();
      await loadJobs();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to stop crawls';
    }
  }

  async function deleteJob(jobId: number) {
    if (!confirm('Delete this crawl job record?')) return;
    try {
      await api.deleteCrawlJob(jobId);
      jobs = jobs.filter(j => j.id !== jobId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete job';
    }
  }

  function getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'var(--color-success)';
      case 'running': return 'var(--color-warning)';
      case 'failed': return 'var(--color-error)';
      case 'cancelled': return 'var(--color-text-secondary)';
      case 'pending': return 'var(--color-primary)';
      default: return 'var(--color-text-secondary)';
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  }

  function isRunning(job: CrawlJob): boolean {
    return job.status === 'running' || job.status === 'pending';
  }
</script>

<div class="crawl-page">
  <header class="page-header">
    <div>
      <h1>Crawl Status</h1>
      <p class="subtitle">
        Monitor your crawl jobs and indexing progress
        {#if activeCount > 0}
          <span class="active-badge">{activeCount} active</span>
        {/if}
      </p>
    </div>
    <div class="header-actions">
      <select class="input" bind:value={statusFilter} onchange={loadJobs}>
        <option value="">All statuses</option>
        <option value="running">Running</option>
        <option value="pending">Pending</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option>
      </select>
      <button class="btn btn-secondary" onclick={loadJobs}>
        Refresh
      </button>
      {#if activeCount > 0}
        <button class="btn btn-secondary btn-danger" onclick={stopAllJobs}>
          Stop All
        </button>
      {/if}
    </div>
  </header>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading crawl status...</div>
  {:else if jobs.length === 0}
    <div class="empty-state card">
      <div class="empty-icon">🔄</div>
      <h2>No Crawl Jobs</h2>
      <p>Start a crawl from the Indexes page to see status here</p>
      <a href="/indexes" class="btn btn-primary">Go to Indexes</a>
    </div>
  {:else}
    <div class="jobs-list">
      {#each jobs as job}
        <article class="job-card card">
          <div class="job-header">
            <div class="job-info">
              <span class="job-id">Job #{job.id}</span>
              <a href={job.source_url || '#'} target="_blank" class="job-url">
                {job.source_url || 'Unknown source'}
              </a>
            </div>
            <div class="job-header-right">
              <span
                class="job-status"
                style="background: {getStatusColor(job.status)}20; color: {getStatusColor(job.status)}"
              >
                {job.status}
              </span>
              <div class="job-actions">
                {#if isRunning(job)}
                  <button
                    class="btn btn-sm btn-secondary"
                    onclick={() => stopJob(job.id)}
                    title="Stop this crawl"
                  >
                    Stop
                  </button>
                {:else}
                  <button
                    class="btn btn-sm btn-secondary btn-danger"
                    onclick={() => deleteJob(job.id)}
                    title="Delete this job record"
                  >
                    Delete
                  </button>
                {/if}
              </div>
            </div>
          </div>

          <div class="job-stats">
            <div class="stat">
              <span class="stat-value">{job.pages_crawled}</span>
              <span class="stat-label">Crawled</span>
            </div>
            <div class="stat">
              <span class="stat-value">{job.pages_indexed}</span>
              <span class="stat-label">Indexed</span>
            </div>
            <div class="stat">
              <span class="stat-value">{job.pages_failed}</span>
              <span class="stat-label">Failed</span>
            </div>
          </div>

          <div class="job-meta">
            <span>Trigger: {job.trigger}</span>
            <span>Started: {formatDate(job.started_at)}</span>
            {#if job.completed_at}
              <span>Completed: {formatDate(job.completed_at)}</span>
            {/if}
          </div>

          {#if job.error_message}
            <div class="job-error">
              {job.error_message}
            </div>
          {/if}
        </article>
      {/each}
    </div>
  {/if}
</div>

<style>
  .crawl-page {
    max-width: 900px;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
    gap: var(--spacing-md);
  }

  .page-header h1 {
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .active-badge {
    background: var(--color-warning);
    color: white;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    font-size: 0.8rem;
    font-weight: 500;
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .header-actions select {
    min-width: 150px;
  }

  .error-message {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

  .loading {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-secondary);
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-xl) * 2;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
  }

  .jobs-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .job-card {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .job-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .job-header-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .job-info {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .job-id {
    font-weight: 600;
  }

  .job-url {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    word-break: break-all;
  }

  .job-status {
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .job-actions {
    display: flex;
    gap: var(--spacing-xs);
  }

  .btn-sm {
    padding: 4px 8px;
    font-size: 0.8rem;
  }

  .btn-danger {
    color: var(--color-error);
  }

  .btn-danger:hover {
    background: #fef2f2;
  }

  .job-stats {
    display: flex;
    gap: var(--spacing-xl);
  }

  .stat {
    display: flex;
    flex-direction: column;
  }

  .stat-value {
    font-size: 1.25rem;
    font-weight: 600;
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .job-meta {
    display: flex;
    gap: var(--spacing-lg);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    flex-wrap: wrap;
  }

  .job-error {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
  }
</style>
