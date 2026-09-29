export enum PipelineRunStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  SUCCESS = 'SUCCESS',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
}

export interface PipelineRunDto {
  id: string;
  projectId: string;
  externalId?: string | null;
  branch?: string | null;
  commitSha?: string | null;
  status: PipelineRunStatus;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectDto {
  id: string;
  name: string;
  slug: string;
  repository?: string | null;
}
