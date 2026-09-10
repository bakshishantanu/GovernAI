-- Supabase Auth Hook / Trigger for GovernAI
-- Assign default role 'agent_builder' and create profile on signup.
-- This ensures self-service signups can never register as 'admin'.

-- 1. Create or replace the handler function
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  -- Set the default role in app_metadata (used in JWT claims)
  UPDATE auth.users
  SET raw_app_meta_data = COALESCE(raw_app_meta_data, '{}'::jsonb) || jsonb_build_object(
    'role', 'agent_builder'
  )
  WHERE id = NEW.id;

  -- Create a profiles row for RBAC lookups
  INSERT INTO public.profiles (id, org_id, role)
  VALUES (
    NEW.id,
    '00000000-0000-0000-0000-000000000000'::uuid,  -- default org (single-tenant MVP)
    'agent_builder'
  )
  ON CONFLICT (id) DO NOTHING;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Create the trigger on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();
