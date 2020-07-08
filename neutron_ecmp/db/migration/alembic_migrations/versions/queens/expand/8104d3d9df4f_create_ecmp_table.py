# Copyright 2019 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
"""create ecmp table

Revision ID: 8104d3d9df4f
Revises:
Create Date: 2020-03-1 18:31:46.794040

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8104d3d9df4f'
down_revision = 'start_ecmp'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'ecmproutes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('vip', sa.String(length=46), nullable=False),
        sa.Column('next_hops', sa.String(length=255), nullable=False),
        sa.Column('router_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['router_id'], ['routers.id'], ondelete='CASCADE')
    )

def downgrade():
    op.drop_table("ecmproutes")