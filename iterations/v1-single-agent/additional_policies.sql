-- Additional policy to allow INSERT operations
-- Run this in your Supabase SQL editor

-- Create policies for insert and update access
create policy "Allow public insert access"
  on site_pages
  for insert
  to public
  with check (true);

create policy "Allow public update access"
  on site_pages
  for update
  to public
  using (true)
  with check (true);
