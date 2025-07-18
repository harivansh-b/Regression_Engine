import React, { useEffect, useState } from 'react';
import { Tooltip } from 'react-tooltip';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import 'react-tooltip/dist/react-tooltip.css';

export default function ModelInference({ target , inferenceDone , setInferenceDone}) {
    const [inferenceData, setInferenceData] = useState(null);
    const [r2Score, setR2Score] = useState(null);
    const [error, setError] = useState('');
    const [inferenceSummary, setInferenceSummary] = useState('');
    const [isLoaded, setIsLoaded] = useState(false);

    useEffect(() => {
        fetch('http://localhost:5000/api/getinference', { credentials: 'include' })
            .then(res => res.json())
            .then(data => {
                if (data.Error) throw new Error(data.Error);
                setInferenceData(data);
                setInferenceSummary(generateOverallSummary(data));
                setTimeout(() => setIsLoaded(true), 100); // Trigger animations
            })
            .catch(err => setError(err.message));

        fetch('http://localhost:5000/api/getmetrics', { credentials: 'include' })
            .then(res => res.json())
            .then(data => {
                if (data.Error) throw new Error(data.Error);
                setR2Score(data.R2);
                setInferenceDone(true);
            })
            .catch(err => setError(err.message));
    }, []);

    const generateSummaryPerFeature = ({ feature, direction, p_val }) => {
        const p = parseFloat(p_val);
        if (p < 0.05) {
            if (direction === 'positive') {
                return `📈 Increase in ${feature} tends to increase ${target}.`;
            } else if (direction === 'negative') {
                return `📉 Increase in ${feature} tends to decrease ${target}.`;
            }
        }
        return `⚠️ ${feature} is not statistically significant for predicting ${target}.`;
    };

    const generateOverallSummary = (data) => {
        const positiveSignificant = [];
        const negativeSignificant = [];
        const notSignificant = [];

        data.forEach(({ feature, direction, p_val }) => {
            const p = parseFloat(p_val);
            if (p < 0.05) {
                direction === 'positive'
                    ? positiveSignificant.push(feature)
                    : negativeSignificant.push(feature);
            } else {
                notSignificant.push(feature);
            }
        });

        let summary = '';

        if (positiveSignificant.length)
            summary += `📈 Features like ${positiveSignificant.join(', ')} are positively and significantly associated with ${target} (p < 0.05).\n\n`;

        if (negativeSignificant.length)
            summary += `📉 Features such as ${negativeSignificant.join(', ')} are negatively and significantly associated with ${target} (p < 0.05).\n\n`;

        if (notSignificant.length)
            summary += `⚠️ Features like ${notSignificant.join(', ')} are not statistically significant (p > 0.05).`;

        return summary.trim();
    };

    if (error) {
        return (
            <div className="text-red-500 p-4 font-montserrat text-lg text-center px-6 py-10 animate-fadeIn">
                {error}
            </div>
        );
    }

    return (
        <div className="min-h-screen flex flex-col items-center justify-start px-6 py-10 font-montserrat space-y-10">
            <style jsx>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                @keyframes float {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-3px); }
                }
                
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.02); }
                }
                
                .animate-fadeIn {
                    animation: fadeIn 0.5s ease-out;
                }
                
                .animate-slideUp {
                    animation: slideUp 0.6s ease-out;
                }
                
                .animate-float {
                    animation: float 2s ease-in-out infinite;
                }
                
                .animate-pulse-scale {
                    animation: pulse 2s ease-in-out infinite;
                }
                
                .hover-lift {
                    transition: transform 0.2s ease;
                }
                
                .hover-lift:hover {
                    transform: translateY(-2px);
                }
                
                tr {
                    transition: background-color 0.2s ease;
                }
                
                tr:hover {
                    background-color: rgba(59, 130, 246, 0.05);
                }
            `}</style>

            <h2 className="text-4xl font-bold text-chrysler-blue-500 text-center">
                🔍 Model Inference
            </h2>

            <div className="text-xl text-chrysler-blue-600 font-semibold text-center">
                📊 Model Accuracy (R²):{' '}
                <span className="text-chrysler-blue-700">
                    {r2Score !== null
                        ? `${(parseFloat(r2Score).toFixed(4) * 100).toFixed(2)}%`
                        : <Skeleton width={80} height={20} />}
                </span>
            </div>

            <div className="flex justify-center w-full animate-slideUp">
                <div className="w-full max-w-6xl overflow-x-auto">
                    <table className="w-full table-auto text-center font-montserrat">
                        <thead>
                            <tr className="text-sm uppercase text-chrysler-blue-700 tracking-wider">
                                <th className="px-6 py-4">Feature</th>
                                <th className="px-6 py-4">Direction</th>
                                <th className="px-6 py-4">p-value</th>
                                <th className="px-6 py-4">Inference</th>
                            </tr>
                        </thead>
                        <tbody>
                            {inferenceData ? (
                                inferenceData.map((item, index) => {
                                    const pVal = parseFloat(item.p_val);
                                    const isSignificant = pVal < 0.05;

                                    return (
                                        <tr 
                                            key={index} 
                                            className="text-chrysler-blue-700 text-sm font-semibold hover-lift"
                                        >
                                            <td className="px-6 py-4">{item.feature}</td>
                                            <td className="px-6 py-4">
                                                <span className={`${
                                                    item.direction === 'positive'
                                                        ? 'text-celadon-300'
                                                        : item.direction === 'negative'
                                                        ? 'text-red-600'
                                                        : 'text-gray-500'
                                                }`}>
                                                    {item.direction}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span
                                                    className="text-chrysler-blue-700 hover-lift"
                                                    data-tooltip-id={`tooltip-${index}`}
                                                >
                                                    {pVal.toFixed(5)}
                                                </span>
                                                <Tooltip
                                                    id={`tooltip-${index}`}
                                                    className="!bg-celadon-300 !text-celadon-800 font-montserrat text-sm px-3 py-1 rounded"
                                                    content={isSignificant ? 'Statistically Significant' : 'Not Statistically Significant'}
                                                />
                                            </td>
                                            <td className="px-6 py-4 text-chrysler-blue-700">
                                                {generateSummaryPerFeature(item)}
                                            </td>
                                        </tr>
                                    );
                                })
                            ) : (
                                [...Array(6)].map((_, idx) => (
                                    <tr key={idx}>
                                        <td className="px-6 py-4"><Skeleton height={20} /></td>
                                        <td className="px-6 py-4"><Skeleton height={20} /></td>
                                        <td className="px-6 py-4"><Skeleton height={20} /></td>
                                        <td className="px-6 py-4"><Skeleton height={20} /></td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="max-w-4xl text-center text-chrysler-blue-600 whitespace-pre-line text-base font-semibold leading-relaxed animate-slideUp animate-pulse-scale">
                {inferenceData ? inferenceSummary : <Skeleton count={3} />}
            </div>
        </div>
    );
}