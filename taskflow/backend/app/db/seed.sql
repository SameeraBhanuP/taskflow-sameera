-- Seed file — safe to run multiple times (ON CONFLICT DO NOTHING)
-- Test credentials: test@example.com / password123
-- Password hash below is bcrypt cost=12 of "password123"

INSERT INTO users (id, name, email, password) VALUES
  ('a0000000-0000-0000-0000-000000000001',
   'Test User',
   'test@example.com',
   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/oJjGcMrCG')
ON CONFLICT (email) DO NOTHING;

INSERT INTO projects (id, name, description, owner_id) VALUES
  ('b0000000-0000-0000-0000-000000000001',
   'Zomato Onboarding',
   'Internal tooling project for the onboarding flow',
   'a0000000-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;

INSERT INTO tasks (id, title, description, status, priority, project_id, assignee_id, due_date) VALUES
  ('c0000000-0000-0000-0000-000000000001',
   'Set up CI pipeline',
   'Configure GitHub Actions for build and test',
   'done', 'high',
   'b0000000-0000-0000-0000-000000000001',
   'a0000000-0000-0000-0000-000000000001',
   '2026-04-10'),
  ('c0000000-0000-0000-0000-000000000002',
   'Design API schema',
   'Draft OpenAPI spec for the onboarding endpoints',
   'in_progress', 'high',
   'b0000000-0000-0000-0000-000000000001',
   'a0000000-0000-0000-0000-000000000001',
   '2026-04-20'),
  ('c0000000-0000-0000-0000-000000000003',
   'Write integration tests',
   'Cover auth and task creation flows',
   'todo', 'medium',
   'b0000000-0000-0000-0000-000000000001',
   NULL,
   '2026-04-30')
ON CONFLICT DO NOTHING;
