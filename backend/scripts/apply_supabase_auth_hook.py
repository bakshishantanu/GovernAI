import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def apply_hook():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        print("Creating public.handle_new_user() function...")
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION public.handle_new_user()
            RETURNS TRIGGER AS $$
            BEGIN
              -- 1. Set the default role in app_metadata (used in JWT claims)
              UPDATE auth.users
              SET raw_app_meta_data = COALESCE(raw_app_meta_data, '{}'::jsonb) || jsonb_build_object(
                'role', 'agent_builder'
              )
              WHERE id = NEW.id;

              -- 2. Create a profiles row for RBAC lookups
              INSERT INTO public.profiles (id, org_id, role)
              VALUES (
                NEW.id,
                '00000000-0000-0000-0000-000000000000'::uuid,
                'agent_builder'
              )
              ON CONFLICT (id) DO NOTHING;

              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        """))
        print("Function created.")

        print("Creating on_auth_user_created trigger on auth.users...")
        await conn.execute(text("""
            DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        """))
        await conn.execute(text("""
            CREATE TRIGGER on_auth_user_created
              AFTER INSERT ON auth.users
              FOR EACH ROW
              EXECUTE FUNCTION public.handle_new_user();
        """))
        print("Trigger created.")

    print("Checking trigger existence...")
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            SELECT tgname FROM pg_trigger WHERE tgname = 'on_auth_user_created';
        """))
        print("Trigger verified:", res.fetchall())

if __name__ == "__main__":
    asyncio.run(apply_hook())
