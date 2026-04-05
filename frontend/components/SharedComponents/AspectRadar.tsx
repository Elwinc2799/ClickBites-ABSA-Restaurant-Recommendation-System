import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getCookie } from 'cookies-next';
import {
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Legend,
    Tooltip,
    TooltipProps,
} from 'recharts';
import UseLoadingAnimation from '../utils/UseLoadingAnimation';
import { UseLoginStatus } from '../utils/UseLoginStatus';

interface VectorScore {
    text: string;
    score: string;
    userScore?: string;
}

interface AspectRadarProps {
    vectorScores: VectorScore[];
    isBusiness: boolean;
    isUser: boolean;
}

interface CustomTooltipProps extends TooltipProps<number, string> {
    isUser: boolean;
    isBusiness: boolean;
    loginStatus: boolean;
}

// Custom tooltip component
const CustomTooltip = ({
    active,
    payload,
    label,
    isUser,
    isBusiness,
    loginStatus,
}: CustomTooltipProps) => {
    if (active && payload && payload.length) {
        return (
            <div
                style={{
                    backgroundColor: '#fff',
                    border: '1px solid #999',
                    margin: '0px',
                    padding: '10px',
                    whiteSpace: 'nowrap',
                }}>
                <p className="label">{`${label}`}</p>
                {payload[0].value && !loginStatus && (
                    <p
                        className="intro"
                        style={{
                            color: payload[0].value < 0 ? 'red' : 'green',
                        }}>{`Business Score: ${payload[0].value}%`}</p>
                )}
                {isUser &&
                    isBusiness &&
                    loginStatus &&
                    payload[1].value &&
                    payload[0] && (
                        <>
                            <p className="intro text-orange-400">{`User Score: ${payload[0].value}%`}</p>
                            <p
                                className="intro"
                                style={{
                                    color:
                                        payload[1].value < 0 ? 'red' : 'green',
                                }}>{`Business Score: ${payload[1].value}%`}</p>
                        </>
                    )}
                {isUser && !isBusiness && loginStatus && payload[0] && (
                    <>
                        <p className="intro text-orange-400">{`User Score: ${payload[0].value}%`}</p>
                    </>
                )}
                {!isUser && isBusiness && loginStatus && payload[0].value && (
                    <>
                        <p
                            className="intro"
                            style={{
                                color: payload[0].value < 0 ? 'red' : 'green',
                            }}>{`Business Score: ${payload[0].value}%`}</p>
                    </>
                )}
            </div>
        );
    }

    return null;
};

const AspectRadar: React.FC<AspectRadarProps> = ({
    vectorScores,
    isBusiness,
    isUser,
}) => {
    const [vectorUserScores, setVectorUserScores] = useState<VectorScore[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    // get user and business vector scores
    useEffect(() => {
        setIsLoading(true);
        const fetchData = async () => {
            const res = await axios.get<{ userId: string }>(
                process.env.API_URL + '/api/getUserId',
                {
                    headers: {
                        Authorization: `Bearer ${getCookie('token')}`,
                    },
                    withCredentials: true,
                }
            );
            return res.data.userId;
        };

        const fetchUserData = async (userId: string) => {
            const res = await axios.get(
                process.env.API_URL + '/api/profile/' + userId,
                {
                    headers: {
                        Authorization: `Bearer ${getCookie('token')}`,
                    },
                    withCredentials: true,
                }
            );
            return res.data;
        };

        const fetchDataAndUserData = async () => {
            const userId = await fetchData();

            const userData = await fetchUserData(userId);

            const newVectorText = ['Food', 'Serv.', 'Pric.', 'Ambi.', 'Misc.'];

            // cast each userData.vector to a string
            let newVector = (userData.preference_vector || userData.vector || []).map(
                (value: number, index: number) => {
                    return {
                        text: newVectorText[index],
                        userScore: (value * 100).toFixed(1).toString(),
                    };
                }
            );

            setVectorUserScores(newVector);
            setIsLoading(false);
        };

        if (UseLoginStatus()) {
            fetchDataAndUserData();
        } else {
            setIsLoading(false);
        }
    }, []);

    // map user and business scores to data 
    const data = vectorScores.map((v: VectorScore, i: number) => ({
        name: v.text + " (%)",
        businessScore: parseFloat(v.score),
        userScore: parseFloat(vectorUserScores[i]?.userScore || '0'),
    }));

    return (
        <>
            {isLoading ? (
                <UseLoadingAnimation isLoading={isLoading} />
            ) : (
                <RadarChart
                    className="text-lg font-medium"
                    cx={500}
                    cy={300}
                    outerRadius={250}
                    width={1000}
                    height={600}
                    data={data}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="name" />
                    <PolarRadiusAxis domain={[0, 100]} />
                    {isUser && UseLoginStatus() && (
                        <Radar
                            name="User Score"
                            dataKey="userScore"
                            stroke="#fb923c"
                            fill="#fb923c"
                            fillOpacity={0.6}
                        />
                    )}
                    {isBusiness && (
                        <Radar
                            name="Business Score"
                            dataKey="businessScore"
                            stroke="#3482F6"
                            fill="#3482F6"
                            fillOpacity={0.6}
                        />
                    )}
                    <Tooltip />
                    <Legend />
                </RadarChart>
            )}
        </>
    );
};

export default AspectRadar;
