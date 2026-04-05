import axios from 'axios';
import React, { useEffect, useState } from 'react';
import { getCookie } from 'cookies-next';
import UseLoadingAnimation from '@/components/utils/UseLoadingAnimation';
import DashboardNavbar from '@/components/NavigationBar/DashboardNavBar';
import DashboardHeader from '@/components/Layout/DashboardHeader';
import CardProfile from '@/components/Dashboard/CardProfile';
import ReviewsTable from '@/components/Dashboard/ReviewsTable';
import AspectRadar from '@/components/SharedComponents/AspectRadar';
import Footer from '@/components/Layout/Footer';

interface Review {
    _id: string;
    user_id: string;
    business_id: string;
    business_name: string;
    business_city: string;
    stars: number;
    text: string;
    date: string;
}
interface Business {
    _id: string;
    name: string;
    address: string;
    city: string;
    state: string;
    latitude: number;
    longitude: number;
    stars: number;
    review_count: number;
    categories: string;
    hours: object;
    description: string;
    view_count: number;
    vector: any;
    business_pic: string;
    reviews: Review[];
}

type VectorScore = {
    text: string;
    score: string;
};

function Dashboard() {
    const [business, setBusiness] = useState<Business | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [vectorScores, setVectorScores] = useState<VectorScore[]>([]);

    // Fetch the business data from the API
    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                const response = await axios.get(
                    `${process.env.API_URL}/api/dashboard`,
                    {
                        headers: {
                            Authorization: `Bearer ${getCookie('token')}`,
                        },
                        withCredentials: true,
                    }
                );

                const raw = response.data;
                const scores = raw.aspect_scores || {};
                const vector = [
                    scores.food ?? 0,
                    scores.service ?? 0,
                    scores.price ?? 0,
                    scores.ambience ?? 0,
                    scores.misc ?? 0,
                ];

                const newVectorText = [
                    'Food',
                    'Service',
                    'Price',
                    'Ambience',
                    'Miscellaneous',
                ];

                let newVector = vector.map(
                    (value: number, index: number) => {
                        return {
                            text: newVectorText[index],
                            score: (value * 100).toFixed(2).toString(),
                        };
                    }
                );

                setVectorScores(newVector);

                const business: Business = {
                    ...raw,
                    _id: raw.business_id || raw._id,
                    business_pic: raw.photo_url || raw.business_pic || null,
                    vector,
                    view_count: raw.view_count || raw.review_count || 0,
                    categories: Array.isArray(raw.categories)
                        ? raw.categories.join(', ')
                        : (raw.categories || ''),
                    reviews: (raw.reviews || []).map((r: any) => ({
                        _id: r.review_id || r._id || '',
                        user_id: r.user_id || '',
                        business_id: raw.business_id || '',
                        business_name: raw.name || '',
                        business_city: raw.city || '',
                        stars: r.stars || 0,
                        text: r.text || '',
                        date: r.created_at || r.date || '',
                    })),
                };

                setBusiness(business);
            } catch (error) {
                console.log(
                    'There was an error fetching the business data',
                    error
                );
            }
            setIsLoading(false);
        };

        fetchData();
    }, []);

    return (
        <>
            {isLoading ? (
                <UseLoadingAnimation isLoading={isLoading} />
            ) : (
                <>
                    <div className="bg-[#1f283b] relative h-44">
                        <DashboardNavbar />

                        <div className="flex flex-row justify-start items-start w-full px-10">
                            <CardProfile business={business} />
                            <div className="flex flex-col justify-start items-center w-8/12 h-52">
                                <DashboardHeader business={business} />
                                <h1 className="text-2xl font-bold leading-relaxed text-gray-900">
                                    Aspect Analysis
                                </h1>
                                <AspectRadar
                                    vectorScores={vectorScores}
                                    isBusiness={true}
                                    isUser={false}
                                />
                            </div>
                        </div>
                        <hr className="mt-9 mb-4 border-1 border-gray-300 mx-10" />
                        <ReviewsTable business={business} />
                        <Footer />
                    </div>
                </>
            )}
        </>
    );
}

export default Dashboard;

