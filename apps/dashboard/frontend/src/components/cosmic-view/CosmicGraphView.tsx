import React from 'react';
import KnowledgeGraph from '../knowledge-graph';

export const CosmicGraphView: React.FC<{ onNodeClick?: (node: any) => void }> = ({ onNodeClick }) => {
    return (
        <div className="relative w-full h-full flex flex-col pointer-events-auto">
            {/* Immersive Graph Container */}
            <div className="absolute inset-0 z-0">
                <KnowledgeGraph onNodeClick={onNodeClick} />
            </div>

            {/* Right Side Tools */}

            {/* Right Side Tools */}
            <div className="absolute top-4 right-4 z-10 w-64 pointer-events-none">
                {/* Context sensitive actions could go here */}
            </div>
        </div>
    );
};
